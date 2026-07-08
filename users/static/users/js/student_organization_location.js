(function () {
    const latInput = document.getElementById('id_organization_latitude');
    const lngInput = document.getElementById('id_organization_longitude');
    const locationInput = document.getElementById('id_organization_location');
    const roadInput = document.getElementById('id_organization_main_road');
    const searchButton = document.getElementById('search-btn');
    const myLocationButton = document.getElementById('my-location-btn');

    if (!latInput || !lngInput || !locationInput || !roadInput || !searchButton || !myLocationButton) {
        return;
    }

    const initialLat = parseFloat(latInput.value || '-1.286389');
    const initialLng = parseFloat(lngInput.value || '36.817223');

    const map = L.map('location-map').setView([initialLat, initialLng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const marker = L.marker([initialLat, initialLng], { draggable: true }).addTo(map);

    function setPosition(lat, lng) {
        marker.setLatLng([lat, lng]);
        map.setView([lat, lng], 15);
        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);
    }

    async function reverseGeocode(lat, lng) {
        try {
            const response = await fetch('https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=' + lat + '&lon=' + lng);
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            const address = data.address || {};

            if (!locationInput.value || locationInput.value.trim() === '') {
                locationInput.value = data.display_name || '';
            }

            const detectedRoad = address.road || address.highway || address.pedestrian || '';
            if (detectedRoad) {
                roadInput.value = detectedRoad;
            }
        } catch (error) {
            // Ignore reverse-geocoding failures and allow manual entry.
        }
    }

    map.on('click', function (event) {
        const lat = event.latlng.lat;
        const lng = event.latlng.lng;
        setPosition(lat, lng);
        reverseGeocode(lat, lng);
    });

    marker.on('dragend', function () {
        const position = marker.getLatLng();
        setPosition(position.lat, position.lng);
        reverseGeocode(position.lat, position.lng);
    });

    searchButton.addEventListener('click', async function () {
        const query = document.getElementById('location-search').value.trim();
        if (!query) {
            return;
        }

        try {
            const response = await fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&q=' + encodeURIComponent(query));
            if (!response.ok) {
                return;
            }
            const results = await response.json();
            if (!results || !results.length) {
                return;
            }

            const best = results[0];
            const lat = parseFloat(best.lat);
            const lng = parseFloat(best.lon);
            setPosition(lat, lng);
            locationInput.value = best.display_name || query;
            reverseGeocode(lat, lng);
        } catch (error) {
            // Ignore search failures and allow manual entry.
        }
    });

    myLocationButton.addEventListener('click', function () {
        if (!navigator.geolocation) {
            return;
        }

        navigator.geolocation.getCurrentPosition(function (position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            setPosition(lat, lng);
            reverseGeocode(lat, lng);
        });
    });

    if (!latInput.value || !lngInput.value) {
        setPosition(initialLat, initialLng);
    } else {
        reverseGeocode(initialLat, initialLng);
    }
})();
