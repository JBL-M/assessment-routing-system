(function () {
    const backButton = document.getElementById('back-button');
    if (!backButton) {
        return;
    }

    backButton.addEventListener('click', function () {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = '/';
        }
    });
})();
