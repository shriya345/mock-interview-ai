let ws = null;
let sessionId = null;
let nextQuestionData = null;
let pendingReport = null;
let currentQuestionNumber = 1;

async function startInterview() {
    const name = document.getElementById('name-input').value.trim();
    const role = document.getElementById('role-select').value;
    const difficulty = document.getElementById('difficulty-select').value;

    if (!name) { alert('Please enter your name'); return; }

    const response = await fetch('/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, role, difficulty })
    });

    const data = await response.json();
    sessionId = data.session_id;
    currentQuestionNumber = 1;

    document.getElementById('setup-screen').style.display = 'none';
    document.getElementById('interview-screen').style.display = 'block';
    document.getElementById('question-text').textContent = data.question;
    document.getElementById('role-badge').textContent = role;
    document.getElementById('progress-text').textContent = `Question 1 of ${data.total_questions}`;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/${sessionId}`);

    ws.onopen = () => console.log('WebSocket connected');
    ws.onerror = (e) => console.error('WebSocket error:', e);
    ws.onclose = (e) => console.log('WebSocket closed:', e.code, e.reason);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };
}

function handleMessage(msg) {

    if (msg.type === 'evaluation_start') {
        document.getElementById('feedback-box').style.display = 'block';
        document.getElementById('feedback-text').textContent = 'Analyzing your answer...';
        document.getElementById('score-display').style.display = 'none';
        document.getElementById('next-btn').style.display = 'none';
        document.getElementById('submit-btn').disabled = true;
    }

    if (msg.type === 'feedback_token') {
        document.getElementById('feedback-text').textContent = msg.content;
    }

    if (msg.type === 'score') {
        const score = msg.data;
        document.getElementById('score-display').style.display = 'flex';
        document.getElementById('tech-score').textContent = `${score.technical}/10`;
        document.getElementById('comm-score').textContent = `${score.communication}/10`;
        document.getElementById('suggestion-text').textContent = `Tip: ${score.suggestion}`;
        document.getElementById('submit-btn').disabled = false;

        const nextBtn = document.getElementById('next-btn');
        nextBtn.style.display = 'block';

        // If report is waiting (Q3 already done), show View Report
        if (pendingReport) {
            nextBtn.textContent = 'View Final Report →';
            nextBtn.onclick = () => showReport(pendingReport);
        } else if (currentQuestionNumber < 3) {
            // More questions coming
            nextBtn.textContent = 'Next Question →';
            nextBtn.onclick = nextQuestion;
        }
        // If Q3 and no report yet, wait for interview_complete message
    }

    if (msg.type === 'next_question') {
        nextQuestionData = msg;
    }

    if (msg.type === 'interview_complete') {
        pendingReport = msg.report;
        const nextBtn = document.getElementById('next-btn');
        nextBtn.textContent = 'View Final Report →';
        nextBtn.style.display = 'block';
        nextBtn.onclick = () => showReport(pendingReport);
    }
}

function submitAnswer() {
    const answer = document.getElementById('answer-input').value.trim();
    if (!answer) { alert('Please type an answer first'); return; }
    ws.send(JSON.stringify({ type: 'answer', answer }));
}

function nextQuestion() {
    if (!nextQuestionData) return;
    currentQuestionNumber++;
    document.getElementById('question-text').textContent = nextQuestionData.question;
    document.getElementById('progress-text').textContent = `Question ${nextQuestionData.number} of 3`;
    document.getElementById('answer-input').value = '';
    document.getElementById('feedback-box').style.display = 'none';
    document.getElementById('next-btn').style.display = 'none';
    nextQuestionData = null;
    pendingReport = null;
}

function showReport(report) {
    document.getElementById('interview-screen').style.display = 'none';
    document.getElementById('report-screen').style.display = 'block';
    document.getElementById('report-content').innerHTML = `
        <div class="report-card">
            <h3>${report.name} — ${report.role}</h3>
            <div class="final-scores">
                <div class="score-card">
                    <span>Technical Avg</span>
                    <strong>${report.avg_technical}/10</strong>
                </div>
                <div class="score-card">
                    <span>Communication Avg</span>
                    <strong>${report.avg_communication}/10</strong>
                </div>
            </div>
            <div class="verdict verdict-${report.overall_verdict.toLowerCase().replace(' ', '-')}">
                Overall: ${report.overall_verdict}
            </div>
        </div>
    `;
}