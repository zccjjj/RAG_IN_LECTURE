import time
import logging
import requests

logger = logging.getLogger(__name__)


def generate_answer(question, retrieved_chunks, ollama_url="http://localhost:11434",
                    model="qwen2.5:7b", temperature=0.3, max_tokens=1024, max_retries=3):
    """
    基于检索到的上下文，使用 Ollama LLM 生成答案（带重试）。
    """
    # 拼接检索到的上下文
    context = "\n\n---\n\n".join([
        chunk["text"] if isinstance(chunk, dict) and "text" in chunk else str(chunk)
        for chunk in retrieved_chunks
    ])

    prompt = f"""你是一个教学视频内容分析助手。请根据以下视频内容片段，准确回答用户的问题。
如果提供的内容中找不到答案，请如实说明。回答应当简洁、准确、有条理。

## 视频内容片段：
{context}

## 问题：
{question}

## 回答："""

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{ollama_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的教学内容分析助手，帮助用户理解视频中的教学内容。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=180
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                logger.warning(f"LLM attempt {attempt+1} failed, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                logger.error(f"LLM generation failed after {max_retries} attempts: {e}")
                return f"生成答案失败: {str(e)}"


def answer_questions(questions, vector_store, embedding_model,
                     ollama_url="http://localhost:11434",
                     model="qwen2.5:7b", top_k=4):
    """
    对所有问题进行检索增强问答。

    Args:
        questions: 问题列表
        vector_store: VectorStore 实例
        embedding_model: EmbeddingModel 实例
        ollama_url: Ollama 服务地址
        model: 文本模型名称
        top_k: 每个问题检索的块数

    Returns:
        问答结果列表: [{"question", "answer", "sources"}, ...]
    """
    results = []

    for i, question in enumerate(questions):
        logger.info(f"Answering question {i+1}/{len(questions)}: {question}")

        # 1. 向量化问题
        q_embedding = embedding_model.encode_single(question)

        # 2. 检索相关文本块
        retrieved = vector_store.query(q_embedding, top_k=top_k)
        chunks_text = [r["chunk"] for r in retrieved]

        # 3. 生成答案
        answer = generate_answer(question, chunks_text, ollama_url, model)

        # 4. 记录来源时间戳
        sources = []
        for r in retrieved:
            chunk = r["chunk"]
            if isinstance(chunk, dict) and "start" in chunk:
                sources.append(chunk["start"])

        results.append({
            "question": question,
            "answer": answer,
            "sources": sources
        })

    logger.info(f"All {len(questions)} questions answered")
    return results
