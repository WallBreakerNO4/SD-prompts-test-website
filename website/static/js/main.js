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

// 观察可见区域附近的图片
function observeVisibleImages() {
    const viewportHeight = window.innerHeight;
    const images = document.querySelectorAll('.matrix-image[data-src]');
    
    images.forEach(img => {
        const imgRect = img.getBoundingClientRect();
        // 观察视口上下300px范围内的图片
        if (imgRect.top > -300 && imgRect.top < viewportHeight + 300) {
            imageObserver.observe(img);
        } else {
            imageObserver.unobserve(img);
        }
    });
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始观察可见区域的图片
    observeVisibleImages();

    // 添加滚动监听器（带防抖）
    window.addEventListener('scroll', debounce(observeVisibleImages, 100));

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

// 跳转到指定行
function jumpToRow() {
    const rowNumber = document.getElementById('rowNumber').value;
    const targetRow = document.getElementById(`row-${rowNumber}`);
    
    if (targetRow) {
        // 暂停所有图片加载
        imageObserver.disconnect();
        
        // 移除之前的高亮效果
        const previousHighlight = document.querySelector('.highlight-animation');
        if (previousHighlight) {
            previousHighlight.classList.remove('highlight-animation');
        }
        
        // 计算目标位置
        const headerHeight = document.querySelector('h1').offsetHeight + 40;
        const targetTop = targetRow.offsetTop - headerHeight;
        
        // 强制禁用平滑滚动并直接跳转
        document.documentElement.style.scrollBehavior = 'auto';
        window.scrollTo(0, targetTop);
        
        // 添加高亮效果
        targetRow.classList.add('highlight-animation');
        
        // 1.5秒后移除高亮类
        setTimeout(() => {
            targetRow.classList.remove('highlight-animation');
        }, 1500);
        
        // 延迟一下再开始观察图片，等待页面稳定
        setTimeout(observeVisibleImages, 100);
    }
}