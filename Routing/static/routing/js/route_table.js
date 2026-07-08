(function () {
    const printButton = document.getElementById('print-route-view');
    if (printButton) {
        printButton.addEventListener('click', function () {
            const originalTitle = document.title;
            const now = new Date();
            const stamp = [
                now.getFullYear(),
                String(now.getMonth() + 1).padStart(2, '0'),
                String(now.getDate()).padStart(2, '0')
            ].join('-');

            document.title = 'optimized-route-' + stamp;

            if (window.optimizedRouteMap) {
                window.optimizedRouteMap.invalidateSize();
            }

            setTimeout(function () {
                window.print();
                setTimeout(function () {
                    document.title = originalTitle;
                }, 300);
            }, 250);
        });
    }

    const mapElement = document.getElementById('optimized-route-map');
    if (!mapElement) {
        return;
    }

    const optimizedPoints = JSON.parse(document.getElementById('optimized-map-points').textContent || '[]');
    const routeStartPoint = JSON.parse(document.getElementById('route-start-point').textContent || '{}');
    const routePathPoints = JSON.parse(document.getElementById('route-path-points').textContent || '[]');

    const map = L.map('optimized-route-map').setView([-1.286389, 36.817223], 11);
    window.optimizedRouteMap = map;

    window.addEventListener('beforeprint', function () {
        if (window.optimizedRouteMap) {
            window.optimizedRouteMap.invalidateSize();
        }
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const routeCoordinates = [];

    if (routeStartPoint && routeStartPoint.lat !== null && routeStartPoint.lng !== null) {
        routeCoordinates.push([routeStartPoint.lat, routeStartPoint.lng]);
        L.marker([routeStartPoint.lat, routeStartPoint.lng]).addTo(map)
            .bindPopup('Start: ' + (routeStartPoint.label || 'Current Location'));
    }

    optimizedPoints.forEach(function (point, index) {
        routeCoordinates.push([point.lat, point.lng]);
        L.marker([point.lat, point.lng]).addTo(map)
            .bindPopup(
                '<strong>Stop ' + (index + 1) + ': ' + point.name + '</strong><br>' +
                point.organization + '<br>' +
                point.location + '<br>' +
                'School ID: ' + (point.school_id || 'N/A') + '<br>' +
                'Course: ' + (point.course || 'N/A') + '<br>' +
                'Attachment Type: ' + (point.attachment_type || 'Not set') + '<br>' +
                'Main Road: ' + (point.main_road || 'Road not set') + '<br>' +
                'From supervisor: ' + point.direct_time_label + '<br>' +
                'ETA in route: ' + point.eta_time_label
            );
    });

    if (routePathPoints.length > 1) {
        L.polyline(routePathPoints, { color: '#146c43', weight: 6, opacity: 0.9 }).addTo(map);
    } else if (routeCoordinates.length > 1) {
        L.polyline(routeCoordinates, { color: '#146c43', weight: 6, dashArray: '6 6', opacity: 0.9 }).addTo(map);
    }

    if (routeCoordinates.length) {
        const bounds = L.latLngBounds(routeCoordinates);
        map.fitBounds(bounds.pad(0.2));
    }
})();
