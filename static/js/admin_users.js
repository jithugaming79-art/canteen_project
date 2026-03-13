/**
 * Admin Users Management
 * Handles AJAX actions for user management
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = window.usersConfig.csrf || getCookie('csrftoken');

function toggleUserStatus(userId, checkbox) {
    const originalState = !checkbox.checked;

    // Optimistic UI update (already handled by checkbox change), 
    // but we might need to revert if API fails.

    const formData = new FormData();
    formData.append('action', 'toggle_status');
    formData.append('user_id', userId);

    fetch(window.usersConfig.apiUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Optional: Show a toast notification
                console.log('User status updated:', data.status);

                // Find the status badge row (traversing up to tr then down to status cell)
                // This is a bit tricky since the badge is in a different cell than the toggle
                // We can reload or try to update DOM if we had IDs.
                // For now, simpler to leave as is or reload page if strict consistency needed.
            } else {
                console.error('Error:', data.message);
                alert('Failed to update status: ' + data.message);
                checkbox.checked = originalState; // Revert
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error occurred');
            checkbox.checked = originalState; // Revert
        });
}

function confirmDeleteUser(userId, username) {
    if (confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        deleteUser(userId);
    }
}

function deleteUser(userId) {
    const formData = new FormData();
    formData.append('action', 'delete');
    formData.append('user_id', userId);

    fetch(window.usersConfig.apiUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the row from the table
                const row = document.querySelector(`button[onclick*="'${userId}'"]`).closest('tr');
                if (row) {
                    row.remove();
                }
                // Optional: update counts
                location.reload(); // Simple way to refresh counts and pagination
            } else {
                alert('Failed to delete user: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error occurred');
        });
}
