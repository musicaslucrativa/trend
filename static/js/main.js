/**
 * Funções principais para a aplicação Trend
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicialização do upload de arquivos
    initFileUpload();
    
    // Inicialização do preview de mídia
    initMediaPreview();
    
    // Animações de entrada
    animateEntrance();
    
    // Inicializar formulários
    initForms();
});

/**
 * Inicializa a funcionalidade de upload de arquivos
 */
function initFileUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.querySelector('.file-input');
    
    if (!uploadArea || !fileInput) return;
    
    // Evento de clique na área de upload
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Eventos de arrastar e soltar
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function() {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    // Evento de seleção de arquivo
    fileInput.addEventListener('change', function() {
        if (fileInput.files.length) {
            handleFileSelect(fileInput.files[0]);
        }
    });
}

/**
 * Manipula a seleção de arquivo
 */
function handleFileSelect(file) {
    const imageContainer = document.getElementById('imageContainer');
    const videoContainer = document.getElementById('videoContainer');
    const previewImg = document.getElementById('previewImg');
    const previewVideo = document.getElementById('previewVideo');
    const previewInfo = document.getElementById('previewInfo');
    const mediaPreview = document.getElementById('mediaPreview');
    
    if (!mediaPreview) return;
    
    // Mostrar área de preview
    mediaPreview.style.display = 'block';
    
    // Exibir informações do arquivo
    if (previewInfo) {
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        previewInfo.textContent = `${file.name} (${fileSize} MB)`;
    }
    
    // Verificar se é um vídeo ou imagem
    const isVideo = file.type.startsWith('video/');
    
    if (isVideo && videoContainer && previewVideo) {
        // Mostrar vídeo, esconder imagem
        videoContainer.style.display = 'block';
        if (imageContainer) imageContainer.style.display = 'none';
        
        // Criar URL para o vídeo
        const videoURL = URL.createObjectURL(file);
        previewVideo.src = videoURL;
        previewVideo.onload = function() {
            URL.revokeObjectURL(videoURL);
        };
    } else if (imageContainer && previewImg) {
        // Mostrar imagem, esconder vídeo
        imageContainer.style.display = 'block';
        if (videoContainer) videoContainer.style.display = 'none';
        
        // Criar URL para a imagem
        const imageURL = URL.createObjectURL(file);
        previewImg.src = imageURL;
        previewImg.onload = function() {
            URL.revokeObjectURL(imageURL);
        };
    }
}

/**
 * Inicializa a funcionalidade de preview de mídia
 */
function initMediaPreview() {
    const mediaPreview = document.getElementById('mediaPreview');
    
    if (!mediaPreview) return;
    
    // Inicialmente ocultar a área de preview
    mediaPreview.style.display = 'none';
}

/**
 * Anima a entrada dos elementos na página
 */
function animateEntrance() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach((card, index) => {
        card.classList.add('fade-in');
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

/**
 * Inicializa os formulários
 */
function initForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('[type="submit"]');
            
            if (submitBtn) {
                const originalText = submitBtn.textContent;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loader"></span> Processando...';
                
                // Restaurar o botão após o envio
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 10000); // Timeout de segurança
            }
        });
    });
}

/**
 * Exibe um alerta temporário
 */
function showAlert(message, type = 'success', duration = 5000) {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} fade-in`;
    alertContainer.textContent = message;
    
    document.body.appendChild(alertContainer);
    
    setTimeout(() => {
        alertContainer.classList.remove('fade-in');
        alertContainer.classList.add('fade-out');
        
        setTimeout(() => {
            document.body.removeChild(alertContainer);
        }, 500);
    }, duration);
}

/**
 * Confirma uma ação antes de executá-la
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}
