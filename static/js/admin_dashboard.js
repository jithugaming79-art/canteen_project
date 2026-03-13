/* admin_dashboard.js – Dashboard AJAX polling & chart rendering */
(function () {
    "use strict";

    /* ── Config (injected by template) ── */
    var timeRange = window.__dashConfig.timeRange;
    var statsUrl = window.__dashConfig.statsUrl;
    var chartUrl = window.__dashConfig.chartUrl;

    var revenueChartInstance = null;
    var categoryChartInstance = null;
    var topSellersChartInstance = null;

    /* ── Pulse animation for value changes ── */
    function pulseEl(el) {
        el.style.transition = "none";
        el.style.background = "rgba(252,128,25,0.12)";
        el.style.borderRadius = "6px";
        setTimeout(function () {
            el.style.transition = "background 1.2s ease";
            el.style.background = "transparent";
        }, 50);
    }

    function updateStat(id, newText) {
        var el = document.getElementById(id);
        if (el && el.textContent.trim() !== newText.trim()) {
            el.textContent = newText;
            pulseEl(el);
        }
    }

    /* ── Build recent orders HTML ── */
    function buildRecentOrdersHTML(orders) {
        if (!orders || orders.length === 0) {
            return "<tr><td colspan=\"5\" style=\"text-align:center;padding:30px;color:var(--admin-text-muted);\">No orders yet</td></tr>";
        }
        var html = "";
        for (var i = 0; i < orders.length; i++) {
            var o = orders[i];
            var hue = (o.user_id + 100) % 360;
            var initial = o.username.charAt(0).toUpperCase();
            var itemsHtml = "";
            for (var j = 0; j < o.items.length; j++) {
                itemsHtml += "<span class=\"order-item-chip\">" + o.items[j].quantity + "\u00d7 " + o.items[j].item_name + "</span>";
            }
            if (o.items_count > 2) {
                itemsHtml += "<span class=\"order-item-chip\">+" + (o.items_count - 2) + "</span>";
            }
            html += "<tr>"
                + "<td style=\"font-weight:700;\">#" + o.token_number + "</td>"
                + "<td><div class=\"user-cell\">"
                + "<div class=\"user-cell-avatar\" style=\"background:hsl(" + hue + ",50%,60%);\">" + initial + "</div>"
                + "<div class=\"user-cell-info\"><span class=\"user-cell-name\">" + o.username + "</span></div>"
                + "</div></td>"
                + "<td><div class=\"order-items-cell\">" + itemsHtml + "</div></td>"
                + "<td style=\"font-weight:600;\">\u20b9" + Math.round(o.total_amount) + "</td>"
                + "<td><span class=\"status-badge " + o.status + "\">" + o.status_display + "</span></td>"
                + "</tr>";
        }
        return html;
    }

    /* ── Refresh stats via API ── */
    function refreshStats() {
        fetch(statsUrl + "?range=" + timeRange)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                updateStat("statTotalRevenue", "\u20b9" + Math.round(data.total_revenue));
                updateStat("statTotalOrders", "" + data.total_orders);
                updateStat("statActiveOrders", "" + data.active_orders);
                updateStat("statTotalUsers", "" + data.total_users);
                updateStat("statTodaysRevenue", "\u20b9" + Math.round(data.todays_revenue) + " today");
                updateStat("statTodaysOrders", data.todays_orders + " today");
                updateStat("statNewUsers", "+" + data.new_users + " this week");
                var tbody = document.getElementById("recentOrdersBody");
                if (tbody) { tbody.innerHTML = buildRecentOrdersHTML(data.recent_orders); }
            })
            .catch(function (err) { console.warn("Stats refresh error:", err); });
    }

    /* ── Refresh charts via API ── */
    function refreshCharts() {
        fetch(chartUrl + "?range=" + timeRange)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                /* Revenue trend line chart */
                var trendCtx = document.getElementById("revenueChart");
                if (trendCtx && data.trend && data.trend.length > 0) {
                    var labels = data.trend.map(function (d) { return d.label; });
                    var values = data.trend.map(function (d) { return d.value; });
                    if (revenueChartInstance) {
                        revenueChartInstance.data.labels = labels;
                        revenueChartInstance.data.datasets[0].data = values;
                        if (revenueChartInstance.config.type !== 'line') {
                            revenueChartInstance.destroy();
                            revenueChartInstance = null;
                        } else {
                            revenueChartInstance.update("none");
                        }
                    }

                    if (!revenueChartInstance) {
                        var ctx2d = trendCtx.getContext("2d");
                        var gradient = ctx2d.createLinearGradient(0, 0, 0, 300);
                        gradient.addColorStop(0, "rgba(99, 102, 241, 0.15)");
                        gradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

                        revenueChartInstance = new Chart(trendCtx, {
                            type: 'line',
                            data: {
                                labels: labels,
                                datasets: [{
                                    label: "Revenue",
                                    data: values,
                                    borderColor: "#6366f1",
                                    backgroundColor: gradient,
                                    fill: true,
                                    tension: 0.45,
                                    pointRadius: 0,
                                    pointHoverRadius: 5,
                                    pointHoverBackgroundColor: "#6366f1",
                                    pointHoverBorderWidth: 2,
                                    pointHoverBorderColor: "#fff",
                                    borderWidth: 3
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                interaction: { intersect: false, mode: 'index' },
                                plugins: { legend: { display: false } },
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        grid: { borderDash: [5, 5], color: "#e2e8f0", drawBorder: false },
                                        ticks: { font: { size: 11, family: "'Inter', sans-serif" }, color: "#94a3b8", padding: 10 }
                                    },
                                    x: {
                                        grid: { display: false },
                                        ticks: { font: { size: 11, family: "'Inter', sans-serif" }, color: "#94a3b8", padding: 10 }
                                    }
                                }
                            }
                        });
                    }
                }

                /* Category doughnut chart */
                var catCtx = document.getElementById("categoryChart");
                if (catCtx && data.categories && data.categories.length > 0) {
                    var catLabels = data.categories.map(function (c) { return c.name; });
                    var catValues = data.categories.map(function (c) { return c.value; });
                    var colors = ["#ff5200", "#0984e3", "#00b894", "#e17055", "#6c5ce7", "#fdcb6e", "#d63031", "#00cec9"];
                    if (categoryChartInstance) {
                        categoryChartInstance.data.labels = catLabels;
                        categoryChartInstance.data.datasets[0].data = catValues;
                        categoryChartInstance.data.datasets[0].backgroundColor = colors.slice(0, catLabels.length);
                        categoryChartInstance.update("none");
                    } else {
                        categoryChartInstance = new Chart(catCtx, {
                            type: "doughnut",
                            data: {
                                labels: catLabels,
                                datasets: [{
                                    data: catValues,
                                    backgroundColor: colors.slice(0, catLabels.length),
                                    borderWidth: 0,
                                    hoverOffset: 8
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                cutout: "65%",
                                plugins: {
                                    legend: {
                                        position: "bottom",
                                        labels: { padding: 16, usePointStyle: true, pointStyle: "circle", font: { size: 12 } }
                                    }
                                }
                            }
                        });
                    }
                }

                /* Top Sellers horizontal bar chart */
                var topCtx = document.getElementById("topSellersChart");
                if (topCtx) {
                    var hasData = data.top_sellers && data.top_sellers.length > 0;
                    var wrap = topCtx.parentNode;
                    var msgId = "topSellersNoData";
                    var msg = document.getElementById(msgId);

                    if (hasData) {
                        topCtx.style.display = "block";
                        if (msg) msg.style.display = "none";

                        var topLabels = data.top_sellers.map(function (s) { return s.label; });
                        var topValues = data.top_sellers.map(function (s) { return s.value; });

                        if (topSellersChartInstance) {
                            topSellersChartInstance.customData = data.top_sellers;
                            topSellersChartInstance.data.labels = topLabels;
                            topSellersChartInstance.data.datasets[0].data = topValues;
                            topSellersChartInstance.update("none");
                        } else {
                            var ctx = topCtx.getContext("2d");

                            // Premium SaaS Vertical Gradients
                            var gradients = [
                                { s: "#6366f1", e: "#818cf8" }, // Indigo
                                { s: "#10b981", e: "#34d399" }, // Emerald
                                { s: "#f59e0b", e: "#fbbf24" }, // Amber
                                { s: "#3b82f6", e: "#60a5fa" }, // Blue
                                { s: "#f43f5e", e: "#fb7185" }  // Rose
                            ].map(function (colors) {
                                var g = ctx.createLinearGradient(0, 0, 0, 300); // Vertical gradient
                                g.addColorStop(0, colors.s);
                                g.addColorStop(1, colors.e);
                                return g;
                            });

                            topSellersChartInstance = new Chart(topCtx, {
                                type: "bar",
                                data: {
                                    labels: topLabels,
                                    datasets: [{
                                        label: "Units",
                                        data: topValues,
                                        backgroundColor: gradients,
                                        borderRadius: 8,
                                        borderSkipped: false,
                                        barPercentage: 0.55,
                                        categoryPercentage: 0.8
                                    }]
                                },
                                options: {
                                    indexAxis: 'x',
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    layout: { padding: { top: 40, bottom: 10 } },
                                    animation: { duration: 1200, easing: 'easeOutQuart' },
                                    plugins: {
                                        legend: { display: false },
                                        tooltip: {
                                            backgroundColor: '#1a1d26',
                                            padding: 12,
                                            cornerRadius: 8,
                                            titleFont: { size: 13, weight: 700, family: "'Inter', sans-serif" },
                                            bodyFont: { size: 13, family: "'Inter', sans-serif" },
                                            displayColors: false,
                                            callbacks: {
                                                label: function (context) {
                                                    var val = context.parsed.y;
                                                    var revenue = 0;
                                                    if (context.chart.customData && context.chart.customData[context.dataIndex]) {
                                                        revenue = context.chart.customData[context.dataIndex].revenue;
                                                    }
                                                    return [
                                                        "Units Sold: " + val,
                                                        "Total Revenue: \u20b9" + Math.round(revenue)
                                                    ];
                                                }
                                            }
                                        }
                                    },
                                    scales: {
                                        y: {
                                            display: false,
                                            grid: { display: false },
                                            beginAtZero: true,
                                            grace: '15%' // Extra room for value labels
                                        },
                                        x: {
                                            grid: { display: false },
                                            ticks: {
                                                font: { size: 11, weight: 600, family: "'Inter', sans-serif" },
                                                color: "#64748b",
                                                padding: 12
                                            }
                                        }
                                    }
                                },
                                plugins: [{
                                    id: 'valueLabels',
                                    afterDatasetsDraw: function (chart) {
                                        var ctx = chart.ctx;
                                        chart.data.datasets.forEach(function (dataset, i) {
                                            var meta = chart.getDatasetMeta(i);
                                            meta.data.forEach(function (bar, index) {
                                                var data = dataset.data[index];
                                                ctx.fillStyle = '#1e293b';
                                                ctx.font = 'bold 13px Inter';
                                                ctx.textAlign = 'center';
                                                ctx.textBaseline = 'bottom';
                                                ctx.fillText(data, bar.x, bar.y - 10);
                                            });
                                        });
                                    }
                                }]
                            });
                            topSellersChartInstance.customData = data.top_sellers;
                        }
                    } else {
                        if (topSellersChartInstance) {
                            topSellersChartInstance.destroy();
                            topSellersChartInstance = null;
                        }
                        topCtx.style.display = "none";
                        if (!msg) {
                            msg = document.createElement("p");
                            msg.id = msgId;
                            msg.style.cssText = "text-align:center;color:var(--admin-text-muted);padding:40px;font-size:14px;";
                            msg.textContent = "No sales data yet";
                            wrap.appendChild(msg);
                        } else {
                            msg.style.display = "block";
                        }
                    }
                }
            })
            .catch(function (err) { console.warn("Chart data error:", err); });
    }

    /* ── Initial load + polling ── */
    refreshCharts();
    setInterval(function () { refreshStats(); refreshCharts(); }, 15000);
})();
