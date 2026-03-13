/* admin_orders.js – Orders page AJAX polling */
(function () {
    "use strict";

    var ordersApiUrl = window.__ordersConfig.apiUrl;
    var currentStatus = window.__ordersConfig.status;
    var currentSearch = window.__ordersConfig.search;
    var currentPage = window.__ordersConfig.page;
    var csrfToken = window.__ordersConfig.csrf;

    function updateTabCount(id, count) {
        var el = document.getElementById(id);
        if (el) el.textContent = "(" + count + ")";
    }

    function getNextAction(status) {
        var map = {
            "pending": { val: "confirmed", icon: "<svg viewBox=\"0 0 24 24\"><polyline points=\"20 6 9 17 4 12\"></polyline></svg>", title: "Confirm" },
            // Removed kitchen actions (preparing/ready)
            "ready": { val: "collected", icon: "<svg viewBox=\"0 0 24 24\"><path d=\"M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2\"></path><rect x=\"8\" y=\"2\" width=\"8\" height=\"4\" rx=\"1\" ry=\"1\"></rect></svg>", title: "Mark Collected" }
        };
        return map[status] || null;
    }

    function buildOrderRow(o) {
        var hue = (o.user_id + 100) % 360;
        var initial = o.username.charAt(0).toUpperCase();
        var itemsHtml = "";
        for (var j = 0; j < o.items.length; j++) {
            itemsHtml += "<span class=\"order-item-chip\">" + o.items[j].quantity + "\u00d7 " + (o.items[j].item_name || o.items[j].name) + "</span>";
        }
        if (o.items_count > 2) {
            itemsHtml += "<span class=\"order-item-chip\">+" + (o.items_count - 2) + "</span>";
        }

        var actionsHtml = "<div class=\"action-buttons\">";

        // View Details Button (only action)
        actionsHtml += "<button type=\"button\" class=\"action-btn view\" title=\"View Details\" onclick=\"openOrderModal(" + o.id + ")\">" +
            "<svg viewBox=\"0 0 24 24\"><path d=\"M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z\"></path><circle cx=\"12\" cy=\"12\" r=\"3\"></circle></svg>" +
            "</button>";

        actionsHtml += "</div>";

        var scheduledHtml = o.scheduled_for
            ? "<span class=\"status-badge\" style=\"background:#e0f2fe;color:#0369a1;\">📅 " + o.scheduled_for + "</span>"
            : "<span style=\"color:var(--admin-text-muted);\">-</span>";

        return "<tr>"
            + "<td><input type=\"checkbox\" name=\"order_ids\" value=\"" + o.id + "\"></td>"
            + "<td style=\"font-weight:700;\">#" + o.token_number + "</td>"
            + "<td><div class=\"user-cell\">"
            + "<div class=\"user-cell-avatar\" style=\"background:hsl(" + hue + ",50%,60%);\">" + initial + "</div>"
            + "<div class=\"user-cell-info\"><span class=\"user-cell-name\">" + o.username + "</span>"
            + "<span class=\"user-cell-email\">" + o.email + "</span></div></div></td>"
            + "<td><div class=\"order-items-cell\">" + itemsHtml + "</div></td>"
            + "<td>" + scheduledHtml + "</td>"
            + "<td style=\"font-weight:600;\">\u20b9" + Math.round(o.total_amount) + "</td>"
            + "<td><span class=\"status-badge " + o.status + "\">" + o.status_display + "</span></td>"
            + "<td style=\"font-size:12px;color:var(--admin-text-muted);\">" + o.created_at + "</td>"
            + "<td>" + actionsHtml + "</td>"
            + "</tr>";
    }

    function refreshOrders() {
        var url = ordersApiUrl + "?status=" + currentStatus + "&search=" + encodeURIComponent(currentSearch) + "&page=" + currentPage;
        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                updateTabCount("tabCountAll", data.counts.all);
                updateTabCount("tabCountPending", data.counts.pending);
                updateTabCount("tabCountPreparing", data.counts.preparing);
                updateTabCount("tabCountReady", data.counts.ready);
                updateTabCount("tabCountCompleted", data.counts.completed);

                var allCountEl = document.getElementById("orderCountAll");
                if (allCountEl) allCountEl.textContent = data.counts.all;

                var tbody = document.getElementById("ordersTableBody");
                if (!tbody) return;

                var checked = {};
                var boxes = tbody.querySelectorAll("input[name=\"order_ids\"]");
                for (var i = 0; i < boxes.length; i++) {
                    if (boxes[i].checked) checked[boxes[i].value] = true;
                }

                if (data.orders.length === 0) {
                    tbody.innerHTML = "<tr><td colspan=\"8\"><div class=\"admin-empty\">"
                        + "<div class=\"admin-empty-icon\">\ud83d\udce6</div><h3>No orders found</h3>"
                        + "<p>Try adjusting your filters</p></div></td></tr>";
                } else {
                    var html = "";
                    for (var j = 0; j < data.orders.length; j++) {
                        html += buildOrderRow(data.orders[j]);
                    }
                    tbody.innerHTML = html;
                }

                var newBoxes = tbody.querySelectorAll("input[name=\"order_ids\"]");
                for (var k = 0; k < newBoxes.length; k++) {
                    if (checked[newBoxes[k].value]) newBoxes[k].checked = true;
                }

                var pageInfoEl = document.getElementById("pageInfo");
                if (pageInfoEl) pageInfoEl.textContent = "Page " + data.page + " of " + data.num_pages;
            })
            .catch(function (err) { console.warn("Orders refresh error:", err); });
    }

    window.openOrderModal = function (orderId) {
        var modal = document.getElementById("orderModal");
        var modalBody = document.getElementById("modalBody");
        var modalTitle = document.getElementById("modalTitle");

        if (!modal || !modalBody) return;

        modal.classList.add("show");
        modal.style.display = "flex";
        modalBody.innerHTML = "<div class=\"modal-loading\"><div class=\"modal-spinner\"></div><span>Loading order details\u2026</span></div>";

        fetch(ordersApiUrl + "?detail_id=" + orderId)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    modalBody.innerHTML = "<div class=\"modal-error\">\u26a0\ufe0f " + data.error + "</div>";
                    return;
                }

                modalTitle.textContent = "Order #" + data.token_number;

                // Status class
                var statusClass = data.status || "pending";

                // Info grid
                var html = "<div class=\"modal-info-grid\">" +
                    "<div class=\"modal-info-item\">" +
                    "<div class=\"modal-info-label\">Customer</div>" +
                    "<div class=\"modal-info-value\">" + data.user.username + "</div>" +
                    "</div>" +
                    "<div class=\"modal-info-item\">" +
                    "<div class=\"modal-info-label\">Email</div>" +
                    "<div class=\"modal-info-value\">" + data.user.email + "</div>" +
                    "</div>" +
                    "<div class=\"modal-info-item\">" +
                    "<div class=\"modal-info-label\">Date</div>" +
                    "<div class=\"modal-info-value\">" + data.created_at + "</div>" +
                    "</div>" +
                    (data.scheduled_for ?
                        "<div class=\"modal-info-item\">" +
                        "<div class=\"modal-info-label\">Scheduled For</div>" +
                        "<div class=\"modal-info-value\" style=\"color:#0369a1;font-weight:600;\">📅 " + data.scheduled_for + "</div>" +
                        "</div>" : "") +
                    "<div class=\"modal-info-item\">" +
                    "<div class=\"modal-info-label\">Status</div>" +
                    "<div class=\"modal-info-value\"><span class=\"status-badge " + statusClass + "\">" + data.status_display + "</span></div>" +
                    "</div>" +
                    "<div class=\"modal-info-item\">" +
                    "<div class=\"modal-info-label\">Payment</div>" +
                    "<div class=\"modal-info-value\">" + (data.payment_status || "N/A") + "</div>" +
                    "</div>" +
                    "</div>";

                // Items section
                html += "<div class=\"modal-section\">" +
                    "<div class=\"modal-section-title\">\ud83d\udce6 Order Items</div>" +
                    "<table class=\"modal-items-table\">" +
                    "<thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr></thead>" +
                    "<tbody>";

                for (var i = 0; i < data.items.length; i++) {
                    var item = data.items[i];
                    var name = item.name || item.item_name;
                    var price = parseFloat(item.price) || 0;
                    var qty = parseInt(item.quantity) || 1;
                    var subtotal = price * qty;
                    html += "<tr>" +
                        "<td class=\"modal-item-name\">" + name + "</td>" +
                        "<td>\u00d7" + qty + "</td>" +
                        "<td>\u20b9" + price.toFixed(0) + "</td>" +
                        "<td>\u20b9" + subtotal.toFixed(0) + "</td>" +
                        "</tr>";
                }

                html += "</tbody></table></div>";

                // Total
                html += "<div class=\"modal-total-row\">" +
                    "<span>Grand Total</span>" +
                    "<span class=\"modal-total-amount\">\u20b9" + data.total_amount + "</span>" +
                    "</div>";

                modalBody.innerHTML = html;

                // Footer — only Close
                var footer = modal.querySelector(".admin-modal-footer");
                if (footer) {
                    footer.innerHTML = "<button type=\"button\" class=\"admin-btn admin-btn-outline\" onclick=\"closeOrderModal()\">Close</button>";
                }
            })
            .catch(function (err) {
                modalBody.innerHTML = "<div class=\"modal-error\">\u26a0\ufe0f Failed to load order details</div>";
                console.error(err);
            });
    };

    window.closeOrderModal = function () {
        var modal = document.getElementById("orderModal");
        if (modal) {
            modal.classList.remove("show");
            setTimeout(function () { modal.style.display = "none"; }, 300);
        }
    };

    // Close on backdrop click
    var modal = document.getElementById("orderModal");
    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target === modal) window.closeOrderModal();
        });
    }

    setInterval(refreshOrders, 15000);
})();
