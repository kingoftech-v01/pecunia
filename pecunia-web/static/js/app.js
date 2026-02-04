/**
 * Pecunia - Main JavaScript
 * ============================
 * Alpine.js components, HTMX configuration, and utility functions
 */

// ============================================
// 1. HTMX Configuration
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Configure HTMX defaults
    if (typeof htmx !== 'undefined') {
        htmx.config.defaultSwapStyle = 'innerHTML';
        htmx.config.defaultSettleDelay = 100;
        htmx.config.historyCacheSize = 10;
        htmx.config.refreshOnHistoryMiss = true;

        // Global error handler
        document.body.addEventListener('htmx:responseError', function(event) {
            const status = event.detail.xhr.status;
            let message = 'An error occurred. Please try again.';

            if (status === 401) {
                message = 'Your session has expired. Please log in again.';
                setTimeout(() => window.location.href = '/accounts/login/', 2000);
            } else if (status === 403) {
                message = 'You do not have permission to perform this action.';
            } else if (status === 404) {
                message = 'The requested resource was not found.';
            } else if (status === 422) {
                message = 'Please check your input and try again.';
            } else if (status >= 500) {
                message = 'A server error occurred. Please try again later.';
            }

            showToast(message, 'error');
        });

        // Handle validation errors (422)
        document.body.addEventListener('htmx:beforeSwap', function(event) {
            if (event.detail.xhr.status === 422) {
                event.detail.shouldSwap = true;
                event.detail.isError = false;
            }
        });

        // Show loading state on forms
        document.body.addEventListener('htmx:beforeRequest', function(event) {
            const form = event.detail.elt.closest('form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.classList.add('opacity-50', 'cursor-wait');
                }
            }
        });

        document.body.addEventListener('htmx:afterRequest', function(event) {
            const form = event.detail.elt.closest('form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-50', 'cursor-wait');
                }
            }
        });

        // Handle redirect responses
        document.body.addEventListener('htmx:beforeSwap', function(event) {
            const redirectUrl = event.detail.xhr.getResponseHeader('HX-Redirect');
            if (redirectUrl) {
                window.location.href = redirectUrl;
            }
        });

        // Trigger toast from response headers
        document.body.addEventListener('htmx:afterSwap', function(event) {
            const toastMessage = event.detail.xhr.getResponseHeader('HX-Toast-Message');
            const toastType = event.detail.xhr.getResponseHeader('HX-Toast-Type') || 'success';

            if (toastMessage) {
                showToast(toastMessage, toastType);
            }
        });
    }
});


// ============================================
// 2. Alpine.js Components & Data
// ============================================

document.addEventListener('alpine:init', () => {

    // ----------------------------------------
    // Global Store
    // ----------------------------------------
    Alpine.store('app', {
        sidebarOpen: window.innerWidth >= 1024,
        searchOpen: false,
        notifications: [],

        init() {
            window.addEventListener('resize', () => {
                if (window.innerWidth >= 1024) {
                    this.sidebarOpen = true;
                }
            });
        },

        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },

        openSearch() {
            this.searchOpen = true;
        },

        closeSearch() {
            this.searchOpen = false;
        }
    });

    // ----------------------------------------
    // Confirm Dialog Component
    // ----------------------------------------
    Alpine.data('confirmDialog', (config = {}) => ({
        open: false,
        title: config.title || 'Confirm Action',
        message: config.message || 'Are you sure you want to proceed?',
        confirmText: config.confirmText || 'Confirm',
        cancelText: config.cancelText || 'Cancel',
        variant: config.variant || 'danger', // danger, warning, info
        onConfirm: null,

        show(options = {}) {
            Object.assign(this, options);
            this.open = true;
            document.body.classList.add('overflow-hidden');
        },

        close() {
            this.open = false;
            document.body.classList.remove('overflow-hidden');
            this.onConfirm = null;
        },

        confirm() {
            if (typeof this.onConfirm === 'function') {
                this.onConfirm();
            }
            this.close();
        }
    }));

    // ----------------------------------------
    // Data Table Component
    // ----------------------------------------
    Alpine.data('dataTable', (config = {}) => ({
        items: config.items || [],
        selected: [],
        sortField: config.sortField || null,
        sortDirection: 'asc',
        searchQuery: '',
        currentPage: 1,
        perPage: config.perPage || 10,

        get filteredItems() {
            let result = [...this.items];

            // Search filter
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                result = result.filter(item =>
                    Object.values(item).some(val =>
                        String(val).toLowerCase().includes(query)
                    )
                );
            }

            // Sort
            if (this.sortField) {
                result.sort((a, b) => {
                    let aVal = a[this.sortField];
                    let bVal = b[this.sortField];

                    if (typeof aVal === 'string') {
                        aVal = aVal.toLowerCase();
                        bVal = bVal.toLowerCase();
                    }

                    if (this.sortDirection === 'asc') {
                        return aVal > bVal ? 1 : -1;
                    } else {
                        return aVal < bVal ? 1 : -1;
                    }
                });
            }

            return result;
        },

        get paginatedItems() {
            const start = (this.currentPage - 1) * this.perPage;
            return this.filteredItems.slice(start, start + this.perPage);
        },

        get totalPages() {
            return Math.ceil(this.filteredItems.length / this.perPage);
        },

        sort(field) {
            if (this.sortField === field) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortField = field;
                this.sortDirection = 'asc';
            }
        },

        selectAll(event) {
            if (event.target.checked) {
                this.selected = this.paginatedItems.map(item => item.id);
            } else {
                this.selected = [];
            }
        },

        isSelected(id) {
            return this.selected.includes(id);
        },

        toggleSelect(id) {
            const index = this.selected.indexOf(id);
            if (index > -1) {
                this.selected.splice(index, 1);
            } else {
                this.selected.push(id);
            }
        }
    }));

    // ----------------------------------------
    // Form Validation Component
    // ----------------------------------------
    Alpine.data('formValidation', () => ({
        errors: {},
        touched: {},

        validate(field, value, rules) {
            const errors = [];

            if (rules.required && !value) {
                errors.push('This field is required');
            }

            if (rules.email && value && !this.isValidEmail(value)) {
                errors.push('Please enter a valid email address');
            }

            if (rules.minLength && value && value.length < rules.minLength) {
                errors.push(`Must be at least ${rules.minLength} characters`);
            }

            if (rules.maxLength && value && value.length > rules.maxLength) {
                errors.push(`Must be no more than ${rules.maxLength} characters`);
            }

            if (rules.pattern && value && !rules.pattern.test(value)) {
                errors.push(rules.patternMessage || 'Invalid format');
            }

            if (rules.match && value !== this.$refs[rules.match]?.value) {
                errors.push('Fields do not match');
            }

            this.errors[field] = errors.length > 0 ? errors[0] : null;
            return errors.length === 0;
        },

        isValidEmail(email) {
            return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        },

        touch(field) {
            this.touched[field] = true;
        },

        hasError(field) {
            return this.touched[field] && this.errors[field];
        },

        clearErrors() {
            this.errors = {};
            this.touched = {};
        }
    }));

    // ----------------------------------------
    // Currency Input Component
    // ----------------------------------------
    Alpine.data('currencyInput', (config = {}) => ({
        value: config.value || '',
        displayValue: '',
        currency: config.currency || 'USD',
        locale: config.locale || 'en-US',

        init() {
            this.formatDisplay();
        },

        formatDisplay() {
            if (this.value) {
                const numValue = parseFloat(this.value);
                if (!isNaN(numValue)) {
                    this.displayValue = new Intl.NumberFormat(this.locale, {
                        style: 'currency',
                        currency: this.currency
                    }).format(numValue);
                }
            }
        },

        handleInput(event) {
            // Remove non-numeric characters except decimal
            let val = event.target.value.replace(/[^0-9.]/g, '');

            // Ensure only one decimal point
            const parts = val.split('.');
            if (parts.length > 2) {
                val = parts[0] + '.' + parts.slice(1).join('');
            }

            // Limit to 2 decimal places
            if (parts[1] && parts[1].length > 2) {
                val = parts[0] + '.' + parts[1].slice(0, 2);
            }

            this.value = val;
        },

        handleBlur() {
            this.formatDisplay();
        },

        handleFocus() {
            this.displayValue = this.value;
        }
    }));

    // ----------------------------------------
    // Date Picker Component
    // ----------------------------------------
    Alpine.data('datePicker', (config = {}) => ({
        value: config.value || '',
        open: false,
        currentDate: new Date(),
        selectedDate: null,
        minDate: config.minDate ? new Date(config.minDate) : null,
        maxDate: config.maxDate ? new Date(config.maxDate) : null,

        init() {
            if (this.value) {
                this.selectedDate = new Date(this.value);
                this.currentDate = new Date(this.value);
            }
        },

        get monthName() {
            return this.currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        },

        get daysInMonth() {
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth();
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const days = [];

            // Add empty slots for days before first day of month
            for (let i = 0; i < firstDay.getDay(); i++) {
                days.push(null);
            }

            // Add days of month
            for (let i = 1; i <= lastDay.getDate(); i++) {
                days.push(new Date(year, month, i));
            }

            return days;
        },

        prevMonth() {
            this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 1);
        },

        nextMonth() {
            this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
        },

        selectDate(date) {
            if (!date || this.isDisabled(date)) return;

            this.selectedDate = date;
            this.value = date.toISOString().split('T')[0];
            this.open = false;
        },

        isSelected(date) {
            if (!date || !this.selectedDate) return false;
            return date.toDateString() === this.selectedDate.toDateString();
        },

        isToday(date) {
            if (!date) return false;
            return date.toDateString() === new Date().toDateString();
        },

        isDisabled(date) {
            if (!date) return true;
            if (this.minDate && date < this.minDate) return true;
            if (this.maxDate && date > this.maxDate) return true;
            return false;
        }
    }));

    // ----------------------------------------
    // Chart Data Component
    // ----------------------------------------
    Alpine.data('chartData', (config = {}) => ({
        data: config.data || [],
        type: config.type || 'bar',
        colors: config.colors || ['#0ea5e9', '#d946ef', '#22c55e', '#f59e0b', '#ef4444'],

        get maxValue() {
            return Math.max(...this.data.map(d => d.value));
        },

        getBarHeight(value) {
            return (value / this.maxValue) * 100;
        },

        getColor(index) {
            return this.colors[index % this.colors.length];
        }
    }));
});


// ============================================
// 3. Utility Functions
// ============================================

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 * @param {number} duration - How long to show the toast in ms
 */
function showToast(message, type = 'info', duration = 5000) {
    window.dispatchEvent(new CustomEvent('toast', {
        detail: { message, type, duration }
    }));
}

/**
 * Copy text to clipboard
 * @param {string} text - The text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'error');
        return false;
    }
}

/**
 * Format a number as currency
 * @param {number} amount - The amount to format
 * @param {string} currency - The currency code
 * @param {string} locale - The locale string
 */
function formatCurrency(amount, currency = 'USD', locale = 'en-US') {
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format a date
 * @param {string|Date} date - The date to format
 * @param {object} options - Intl.DateTimeFormat options
 */
function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    return new Date(date).toLocaleDateString('en-US', { ...defaultOptions, ...options });
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {string|Date} date - The date to format
 */
function formatRelativeTime(date) {
    const now = new Date();
    const then = new Date(date);
    const diff = now - then;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 7) {
        return formatDate(date);
    } else if (days > 0) {
        return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
        return 'Just now';
    }
}

/**
 * Debounce function
 * @param {function} func - The function to debounce
 * @param {number} wait - The debounce delay in ms
 */
function debounce(func, wait = 300) {
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

/**
 * Throttle function
 * @param {function} func - The function to throttle
 * @param {number} limit - The throttle limit in ms
 */
function throttle(func, limit = 300) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Download data as file
 * @param {string} data - The data to download
 * @param {string} filename - The filename
 * @param {string} type - The MIME type
 */
function downloadFile(data, filename, type = 'text/plain') {
    const blob = new Blob([data], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Parse query string to object
 * @param {string} queryString - The query string to parse
 */
function parseQueryString(queryString = window.location.search) {
    return Object.fromEntries(new URLSearchParams(queryString));
}

/**
 * Build query string from object
 * @param {object} params - The parameters object
 */
function buildQueryString(params) {
    return new URLSearchParams(params).toString();
}


// ============================================
// 4. Event Listeners
// ============================================

// Handle keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Cmd/Ctrl + K for search
    if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        Alpine.store('app').openSearch();
    }

    // Escape to close modals/search
    if (event.key === 'Escape') {
        Alpine.store('app').closeSearch();
    }
});

// Handle click outside to close dropdowns
document.addEventListener('click', function(event) {
    // Close any open dropdowns when clicking outside
    if (!event.target.closest('[x-data]')) {
        document.querySelectorAll('[x-data]').forEach(el => {
            if (el.__x && el.__x.$data.open) {
                el.__x.$data.open = false;
            }
        });
    }
});

// Log page views for analytics (if needed)
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Pecunia] Page loaded:', window.location.pathname);
});


// ============================================
// 5. Export for module usage
// ============================================

window.Pecunia = {
    showToast,
    copyToClipboard,
    formatCurrency,
    formatDate,
    formatRelativeTime,
    debounce,
    throttle,
    downloadFile,
    parseQueryString,
    buildQueryString
};
