document.querySelectorAll('input[name="formato"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const calidadField = document.querySelector('input[name="calidad"]');
        if (this.id === 'mp4_sd') {
            calidadField.disabled = false;
            calidadField.value = '480';
        } else if (this.id === 'mp4_hd') {
            calidadField.disabled = false;
            calidadField.value = '720';
        } else {
            calidadField.disabled = true;
        }
    });
});

document.querySelector('input[name="url"]').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.querySelector('button[name="analizar"]').click();
    }
});

document.querySelector('form').addEventListener('submit', function(e) {
    const analyzeBtn = document.getElementById('analyze-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    
    if (e.submitter && e.submitter.name === 'analizar') {
        analyzeBtn.classList.add('loading');
        spinner.classList.remove('hidden');
        btnText.textContent = 'Analizando...';
    }
});

window.addEventListener('load', function() {
    const analyzeBtn = document.getElementById('analyze-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    
    if (document.querySelector('.alert')) {
        analyzeBtn.classList.remove('loading');
        spinner.classList.add('hidden');
        btnText.textContent = 'Analizar';
    }
});

function checkProgress() {
    fetch('/progress')
        .then(response => response.json())
        .then(data => {
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            const downloadStatus = document.getElementById('downloadStatus');
            const notification = document.getElementById('notification');
            
            if (data.status === 'downloading' || data.status === 'starting') {
                progressContainer.style.display = 'block';
                progressBar.style.width = data.percentage;
                progressBar.textContent = data.percentage;
                downloadStatus.textContent = 'Descargando...';
            }
            
            if (data.status === 'finished') {
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                downloadStatus.textContent = 'Procesando archivo...';
                
                notification.style.display = 'block';
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 5000);
            }
            
            if (data.status === 'error') {
                progressContainer.style.display = 'none';
            }
            
            if (data.status !== 'finished' && data.status !== 'error') {
                setTimeout(checkProgress, 1000);
            }
        });
}

document.querySelector('button[name="descargar"]')?.addEventListener('click', function() {
    setTimeout(checkProgress, 1000);
});