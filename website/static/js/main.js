// 图片查看器功能
function showImage(src, artist, prompt) {
    const modalImage = document.getElementById('modalImage');
    modalImage.src = src;
    modalImage.alt = `${artist} - ${prompt}`;
}

// 懒加载和预加载配置
const config = {
    rootMargin: '50px 0px', // 提前50px开始加载
    threshold: 0.1 // 当图片出现10%时触发
};

// 创建图片加载观察器
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            loadImage(img);
            observer.unobserve(img); // 加载后停止观察
        }
    });
}, config);

// 预加载队列
const preloadQueue = new Set();
const preloadImage = (url) => {
    if (preloadQueue.has(url)) return;
    preloadQueue.add(url);
    const img = new Image();
    img.src = url;
};

// 加载图片
function loadImage(img) {
    const actualSrc = img.dataset.src;
    if (!actualSrc) return;

    // 设置加载动画
    img.classList.add('loading');
    img.closest('.image-container').classList.add('loading');
    
    // 加载实际图片
    img.src = actualSrc;
    img.removeAttribute('data-src');
    
    // 图片加载完成后
    img.onload = () => {
        img.classList.remove('loading');
        img.classList.add('loaded');
        img.closest('.image-container').classList.remove('loading');
        
        // 预加载周围的图片
        preloadNearbyImages(img);
    };
}

// 预加载周围的图片
function preloadNearbyImages(currentImg) {
    const cell = currentImg.closest('td');
    if (!cell) return;

    // 获取当前行和列的索引
    const row = cell.parentElement;
    const cellIndex = Array.from(row.children).indexOf(cell);
    const rowIndex = Array.from(row.parentElement.children).indexOf(row);
    
    // 预加载周围的图片（上、下、左、右各一个）
    const directions = [
        [-1, 0], // 上
        [1, 0],  // 下
        [0, -1], // 左
        [0, 1]   // 右
    ];
    
    directions.forEach(([rowOffset, cellOffset]) => {
        const targetRow = row.parentElement.children[rowIndex + rowOffset];
        if (targetRow) {
            const targetCell = targetRow.children[cellIndex + cellOffset];
            if (targetCell) {
                const targetImg = targetCell.querySelector('img[data-src]');
                if (targetImg) {
                    preloadImage(targetImg.dataset.src);
                }
            }
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 获取所有图片
    const images = document.querySelectorAll('.matrix-image[data-src]');
    
    // 观察所有图片
    images.forEach(img => {
        imageObserver.observe(img);
    });

    // 添加模态框点击关闭功能
    const modal = document.querySelector('.fullscreen-modal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            // 如果点击的是模态框本身或模态框内容（不是图片），则关闭模态框
            if (event.target.classList.contains('modal-dialog') || 
                event.target.classList.contains('modal-content') ||
                event.target.classList.contains('modal-body')) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            }
        });
    }
});