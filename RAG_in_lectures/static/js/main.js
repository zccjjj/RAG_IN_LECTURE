// 全局状态
let currentSessionId = null;
let pollInterval = null;

// DOM 元素
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');
const uploadForm = document.getElementById('upload-form');
const submitBtn = document.getElementById('submit-btn');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const progressPercent = document.getElementById('progress-percent');
const stageText = document.getElementById('stage-text');
const resultsContainer = document.getElementById('results-container');
const downloadBtn = document.getElementById('download-btn');
const newBtn = document.getElementById('new-btn');
const retryBtn = document.getElementById('retry-btn');
const errorMessage = document.getElementById('error-message');
const videoInput = document.getElementById('video-input');
const fileInfo = document.getElementById('file-info');
const dropZone = document.getElementById('drop-zone');

// 文件选择反馈
videoInput.addEventListener('change', function() {
    if (this.files.length > 0) {
        const file = this.files[0];
        const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
        fileInfo.textContent = `已选择: ${file.name} (${sizeMB} MB)`;
        fileInfo.classList.add('selected');
    }
});

// 拖拽效果
dropZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    this.classList.add('dragover');
});

dropZone.addEventListener('dragleave', function() {
    this.classList.remove('dragover');
});

dropZone.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        videoInput.files = e.dataTransfer.files;
        videoInput.dispatchEvent(new Event('change'));
    }
});

// 表单提交
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const videoFile = videoInput.files[0];
    const questions = document.getElementById('questions-input').value.trim();

    if (!videoFile) {
        alert('请选择视频文件');
        return;
    }
    if (!questions) {
        alert('请输入至少一个问题');
        return;
    }

    // 构建表单数据
    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('questions', questions);

    // 禁用提交按钮
    submitBtn.disabled = true;
    submitBtn.textContent = '上传中...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '上传失败');
        }

        currentSessionId = data.session_id;
        showProgress();
        startPolling();

    } catch (error) {
        showError(error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '开始处理';
    }
});

// 显示进度区域
function showProgress() {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
}

// 显示结果区域
function showResults() {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    errorSection.style.display = 'none';
}

// 显示错误
function showError(message) {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'block';
    errorMessage.textContent = message;
    stopPolling();
}

// 重置为初始状态
function resetUI() {
    uploadSection.style.display = 'block';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    uploadForm.reset();
    fileInfo.textContent = '支持格式: MP4, AVI, MKV, MOV, WebM';
    fileInfo.classList.remove('selected');
    currentSessionId = null;
    stopPolling();
}

// 轮询状态
function startPolling() {
    pollInterval = setInterval(async () => {
        if (!currentSessionId) return;

        try {
            const response = await fetch(`/api/status/${currentSessionId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '获取状态失败');
            }

            // 更新进度条
            progressFill.style.width = `${data.progress}%`;
            progressPercent.textContent = `${data.progress}%`;
            stageText.textContent = data.stage;

            // 检查是否完成
            if (data.stage === 'completed') {
                stopPolling();
                await loadResults();
            } else if (data.stage === 'error') {
                showError(data.error || '处理过程中发生错误');
            }

        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 2000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// 加载结果
async function loadResults() {
    try {
        const response = await fetch(`/api/results/${currentSessionId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '获取结果失败');
        }

        renderResults(data.results);
        showResults();

    } catch (error) {
        showError(error.message);
    }
}

// 渲染结果
function renderResults(results) {
    resultsContainer.innerHTML = '';

    results.forEach((qa, index) => {
        const card = document.createElement('div');
        card.className = 'qa-card';

        let sourcesHTML = '';
        if (qa.sources && qa.sources.length > 0) {
            const times = qa.sources.map(s => formatTime(s)).join(', ');
            sourcesHTML = `<div class="sources">参考时间段: ${times}</div>`;
        }

        card.innerHTML = `
            <div class="question">Q${index + 1}: ${escapeHtml(qa.question)}</div>
            <div class="answer">${escapeHtml(qa.answer)}</div>
            ${sourcesHTML}
        `;

        resultsContainer.appendChild(card);
    });
}

// 格式化时间
function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 下载文档
downloadBtn.addEventListener('click', function() {
    if (currentSessionId) {
        window.location.href = `/api/download/${currentSessionId}`;
    }
});

// 开始新任务
newBtn.addEventListener('click', resetUI);
retryBtn.addEventListener('click', resetUI);
