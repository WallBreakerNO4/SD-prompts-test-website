function showImage(src, artist, prompt) {
    document.getElementById('modalImage').src = src;
    document.getElementById('modalImage').alt = `${artist} - ${prompt}`;
} 