/**
 * Frontend Performance Optimizations
 * - Lazy loading
 * - Code splitting
 * - Virtual scrolling
 * - Debouncing/Throttling
 * - Asset optimization
 */

// ============================================================================
// 1. LAZY LOADING MODULES
// ============================================================================

/**
 * Dynamically import modules only when needed
 */
export async function lazyLoadModule(modulePath) {
    try {
        const module = await import(modulePath);
        return module;
    } catch (error) {
        console.error(`Failed to load module: ${modulePath}`, error);
        return null;
    }
}

// Usage examples:
// const imageGen = await lazyLoadModule('./modules/image-gen.js');
// const exportHandler = await lazyLoadModule('./modules/export-handler.js');


// ============================================================================
// 2. VIRTUAL SCROLLING FOR CHAT
// ============================================================================

/**
 * Virtual scrolling for large message lists
 * Only renders visible messages + buffer
 */
export class VirtualScroller {
    constructor(container, itemHeight = 100, bufferSize = 5) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.bufferSize = bufferSize;
        this.items = [];
        this.visibleStart = 0;
        this.visibleEnd = 0;
        
        this.setupScrollListener();
    }
    
    setItems(items) {
        this.items = items;
        this.updateVisibleRange();
        this.render();
    }
    
    setupScrollListener() {
        let ticking = false;
        
        this.container.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    this.updateVisibleRange();
                    this.render();
                    ticking = false;
                });
                ticking = true;
            }
        });
    }
    
    updateVisibleRange() {
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        
        this.visibleStart = Math.max(
            0,
            Math.floor(scrollTop / this.itemHeight) - this.bufferSize
        );
        
        this.visibleEnd = Math.min(
            this.items.length,
            Math.ceil((scrollTop + containerHeight) / this.itemHeight) + this.bufferSize
        );
    }
    
    render() {
        const visibleItems = this.items.slice(this.visibleStart, this.visibleEnd);
        
        // Clear container
        this.container.innerHTML = '';
        
        // Create spacer for items before visible range
        const topSpacer = document.createElement('div');
        topSpacer.style.height = `${this.visibleStart * this.itemHeight}px`;
        this.container.appendChild(topSpacer);
        
        // Render visible items
        visibleItems.forEach(item => {
            const element = this.createItemElement(item);
            this.container.appendChild(element);
        });
        
        // Create spacer for items after visible range
        const bottomSpacer = document.createElement('div');
        bottomSpacer.style.height = `${(this.items.length - this.visibleEnd) * this.itemHeight}px`;
        this.container.appendChild(bottomSpacer);
    }
    
    createItemElement(item) {
        // Override this method to customize rendering
        const div = document.createElement('div');
        div.className = 'virtual-item';
        div.textContent = item.content || JSON.stringify(item);
        return div;
    }
}


// ============================================================================
// 3. DEBOUNCE & THROTTLE UTILITIES
// ============================================================================

/**
 * Debounce function - delay execution until after wait time
 * Use for: input handlers, resize events
 */
export function debounce(func, wait = 300) {
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
 * Throttle function - execute at most once per wait time
 * Use for: scroll handlers, mousemove events
 */
export function throttle(func, wait = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, wait);
        }
    };
}

// Usage examples:
// const debouncedResize = debounce(() => console.log('Resized!'), 250);
// const throttledScroll = throttle(() => console.log('Scrolling!'), 100);


// ============================================================================
// 4. REQUEST QUEUE & BATCH PROCESSING
// ============================================================================

/**
 * Queue requests to avoid overwhelming the server
 */
export class RequestQueue {
    constructor(maxConcurrent = 3) {
        this.maxConcurrent = maxConcurrent;
        this.queue = [];
        this.running = 0;
    }
    
    async add(requestFn) {
        return new Promise((resolve, reject) => {
            this.queue.push({ requestFn, resolve, reject });
            this.process();
        });
    }
    
    async process() {
        if (this.running >= this.maxConcurrent || this.queue.length === 0) {
            return;
        }
        
        this.running++;
        const { requestFn, resolve, reject } = this.queue.shift();
        
        try {
            const result = await requestFn();
            resolve(result);
        } catch (error) {
            reject(error);
        } finally {
            this.running--;
            this.process(); // Process next
        }
    }
}

// Usage:
// const queue = new RequestQueue(3);
// await queue.add(() => fetch('/api/chat', {...}));


// ============================================================================
// 5. IMAGE OPTIMIZATION
// ============================================================================

/**
 * Compress and resize images before upload
 */
export class ImageOptimizer {
    static async compress(file, maxWidth = 800, quality = 0.8) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    // Calculate new dimensions
                    let width = img.width;
                    let height = img.height;
                    
                    if (width > maxWidth) {
                        height = (height * maxWidth) / width;
                        width = maxWidth;
                    }
                    
                    // Create canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    // Convert to blob
                    canvas.toBlob((blob) => {
                        resolve(new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        }));
                    }, 'image/jpeg', quality);
                };
                img.src = e.target.result;
            };
            
            reader.readAsDataURL(file);
        });
    }
    
    static async compressMultiple(files, maxWidth = 800, quality = 0.8) {
        const promises = files.map(file => 
            file.type.startsWith('image/') 
                ? this.compress(file, maxWidth, quality)
                : Promise.resolve(file)
        );
        return Promise.all(promises);
    }
}

// Usage:
// const compressed = await ImageOptimizer.compress(imageFile, 800, 0.8);


// ============================================================================
// 6. LOCAL STORAGE CACHE
// ============================================================================

/**
 * Client-side caching with localStorage
 */
export class LocalCache {
    static set(key, value, ttl = 3600000) { // Default 1 hour
        const item = {
            value: value,
            expiry: Date.now() + ttl
        };
        localStorage.setItem(key, JSON.stringify(item));
    }
    
    static get(key) {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) return null;
        
        try {
            const item = JSON.parse(itemStr);
            
            // Check if expired
            if (Date.now() > item.expiry) {
                localStorage.removeItem(key);
                return null;
            }
            
            return item.value;
        } catch (error) {
            console.error('Error parsing cached item:', error);
            localStorage.removeItem(key);
            return null;
        }
    }
    
    static remove(key) {
        localStorage.removeItem(key);
    }
    
    static clear() {
        localStorage.clear();
    }
}

// Usage:
// LocalCache.set('user_settings', settings, 3600000);
// const settings = LocalCache.get('user_settings');


// ============================================================================
// 7. WEB WORKER FOR HEAVY TASKS
// ============================================================================

/**
 * Create and manage web workers for CPU-intensive tasks
 */
export class WorkerPool {
    constructor(workerScript, poolSize = 4) {
        this.workers = [];
        this.taskQueue = [];
        
        for (let i = 0; i < poolSize; i++) {
            const worker = new Worker(workerScript);
            worker.busy = false;
            this.workers.push(worker);
        }
    }
    
    async execute(task) {
        return new Promise((resolve, reject) => {
            const availableWorker = this.workers.find(w => !w.busy);
            
            if (availableWorker) {
                this.runTask(availableWorker, task, resolve, reject);
            } else {
                this.taskQueue.push({ task, resolve, reject });
            }
        });
    }
    
    runTask(worker, task, resolve, reject) {
        worker.busy = true;
        
        worker.onmessage = (e) => {
            worker.busy = false;
            resolve(e.data);
            
            // Process next task in queue
            if (this.taskQueue.length > 0) {
                const { task, resolve, reject } = this.taskQueue.shift();
                this.runTask(worker, task, resolve, reject);
            }
        };
        
        worker.onerror = (error) => {
            worker.busy = false;
            reject(error);
        };
        
        worker.postMessage(task);
    }
    
    terminate() {
        this.workers.forEach(worker => worker.terminate());
        this.workers = [];
    }
}

// Usage:
// const pool = new WorkerPool('/static/js/workers/markdown-worker.js', 4);
// const result = await pool.execute({ type: 'parse', content: markdown });


// ============================================================================
// 8. INTERSECTION OBSERVER FOR LAZY LOADING
// ============================================================================

/**
 * Lazy load images when they come into view
 */
export class LazyLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: '50px',
            threshold: 0.01,
            ...options
        };
        
        this.observer = new IntersectionObserver(
            this.handleIntersection.bind(this),
            this.options
        );
    }
    
    observe(element) {
        this.observer.observe(element);
    }
    
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                
                // Load image
                if (element.dataset.src) {
                    element.src = element.dataset.src;
                    element.removeAttribute('data-src');
                }
                
                // Load background image
                if (element.dataset.bgSrc) {
                    element.style.backgroundImage = `url(${element.dataset.bgSrc})`;
                    element.removeAttribute('data-bg-src');
                }
                
                // Stop observing
                this.observer.unobserve(element);
            }
        });
    }
}

// Usage:
// const lazyLoader = new LazyLoader();
// document.querySelectorAll('img[data-src]').forEach(img => {
//     lazyLoader.observe(img);
// });


// ============================================================================
// 9. PERFORMANCE MONITORING
// ============================================================================

/**
 * Monitor and log performance metrics
 */
export class PerformanceMonitor {
    static marks = {};
    
    static start(name) {
        this.marks[name] = performance.now();
    }
    
    static end(name) {
        if (!this.marks[name]) {
            console.warn(`No start mark for: ${name}`);
            return null;
        }
        
        const duration = performance.now() - this.marks[name];
        delete this.marks[name];
        
        console.log(`⏱️ ${name}: ${duration.toFixed(2)}ms`);
        return duration;
    }
    
    static measure(name, fn) {
        this.start(name);
        const result = fn();
        this.end(name);
        return result;
    }
    
    static async measureAsync(name, fn) {
        this.start(name);
        const result = await fn();
        this.end(name);
        return result;
    }
    
    static getNavigationTiming() {
        const timing = performance.getEntriesByType('navigation')[0];
        return {
            dns: timing.domainLookupEnd - timing.domainLookupStart,
            tcp: timing.connectEnd - timing.connectStart,
            request: timing.responseStart - timing.requestStart,
            response: timing.responseEnd - timing.responseStart,
            domLoad: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
            pageLoad: timing.loadEventEnd - timing.loadEventStart,
            total: timing.loadEventEnd - timing.fetchStart
        };
    }
}

// Usage:
// PerformanceMonitor.start('render');
// renderMessages();
// PerformanceMonitor.end('render');
//
// const result = await PerformanceMonitor.measureAsync('api-call', () => 
//     fetch('/api/chat', {...})
// );


// ============================================================================
// 10. EXAMPLE: OPTIMIZED MAIN.JS INTEGRATION
// ============================================================================

/**
 * Example of how to integrate these optimizations into main.js
 */
export class OptimizedChatApp {
    constructor() {
        // Lazy load heavy modules
        this.imageGen = null;
        this.exportHandler = null;
        
        // Performance utilities
        this.requestQueue = new RequestQueue(3);
        this.lazyLoader = new LazyLoader();
        
        // Debounced/throttled handlers
        this.debouncedResize = debounce(this.handleResize.bind(this), 250);
        this.throttledScroll = throttle(this.handleScroll.bind(this), 100);
    }
    
    async init() {
        PerformanceMonitor.start('app-init');
        
        // Load critical modules first
        await this.loadCriticalModules();
        
        // Setup event listeners with optimized handlers
        window.addEventListener('resize', this.debouncedResize);
        window.addEventListener('scroll', this.throttledScroll);
        
        // Setup lazy loading for images
        document.querySelectorAll('img[data-src]').forEach(img => {
            this.lazyLoader.observe(img);
        });
        
        PerformanceMonitor.end('app-init');
    }
    
    async loadCriticalModules() {
        // Load only what's needed initially
        const { ChatManager } = await import('./modules/chat-manager.js');
        const { APIService } = await import('./modules/api-service.js');
        
        this.chatManager = new ChatManager();
        this.apiService = new APIService();
    }
    
    async loadImageGenModule() {
        if (!this.imageGen) {
            const module = await lazyLoadModule('./modules/image-gen.js');
            this.imageGen = new module.ImageGeneration(this.apiService);
        }
        return this.imageGen;
    }
    
    async sendMessage(message) {
        // Queue request to avoid overwhelming server
        return this.requestQueue.add(async () => {
            const response = await PerformanceMonitor.measureAsync('send-message', () =>
                this.apiService.sendMessage(message)
            );
            return response;
        });
    }
    
    handleResize() {
        console.log('Window resized (debounced)');
    }
    
    handleScroll() {
        console.log('Scrolling (throttled)');
    }
}


// ============================================================================
// EXPORTS
// ============================================================================

export {
    VirtualScroller,
    debounce,
    throttle,
    RequestQueue,
    ImageOptimizer,
    LocalCache,
    WorkerPool,
    LazyLoader,
    PerformanceMonitor
};
