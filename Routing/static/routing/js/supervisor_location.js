(function () {
    const latInput = document.getElementById('current-lat-input');
    const lngInput = document.getElementById('current-lng-input');
    const useBrowserLocationButton = document.getElementById('use-browser-location');

    if (!latInput || !lngInput || !useBrowserLocationButton) {
        return;
    }

    const hasSavedPoint = latInput.value !== '' && lngInput.value !== '';
    const initialLat = hasSavedPoint ? Number(latInput.value) : -1.286389;
    const initialLng = hasSavedPoint ? Number(lngInput.value) : 36.817223;

    const map = L.map('supervisor-location-map').setView([initialLat, initialLng], hasSavedPoint ? 14 : 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let marker = null;

    function setMarker(lat, lng) {
        if (marker) {
            marker.setLatLng([lat, lng]);
        } else {
            marker = L.marker([lat, lng], { draggable: true }).addTo(map);
            marker.on('dragend', function () {
                const position = marker.getLatLng();
                latInput.value = position.lat.toFixed(6);
                lngInput.value = position.lng.toFixed(6);
            });
        }

        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);
    }

    if (hasSavedPoint) {
        setMarker(initialLat, initialLng);
    }

    map.on('click', function (event) {
        setMarker(event.latlng.lat, event.latlng.lng);
    });

    useBrowserLocationButton.addEventListener('click', function () {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported in this browser.');
            return;
        }

        navigator.geolocation.getCurrentPosition(function (position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            setMarker(lat, lng);
            map.setView([lat, lng], 15);
        }, function () {
            alert('Could not get your current location. You can click on the map manually.');
        });
    });
})();
