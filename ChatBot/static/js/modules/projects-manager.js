/**
 * Projects Manager Module
 * Organizes chats into projects with shared learning and context
 * Enables cross-chat knowledge sharing and project-based organization
 */

export default class ProjectsManager {
    constructor(chatManager, memoryManager) {
        this.chatManager = chatManager;
        this.memoryManager = memoryManager;
        this.projects = new Map(); // projectId -> project data
        this.activeProjectId = null;
        this.initialized = false;
    }

    /**
     * Initialize projects manager
     */
    async init() {
        console.log('📁 Initializing Projects Manager...');
        
        // Load projects from storage
        await this.loadProjects();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Render projects UI
        this.renderProjectsList();
        
        // Load active project if exists
        if (this.activeProjectId) {
            await this.loadProject(this.activeProjectId);
        }
        
        this.initialized = true;
        console.log('✅ Projects Manager initialized');
    }

    /**
     * Setup event listeners for projects UI
     */
    setupEventListeners() {
        // New project button
        const newProjectBtn = document.getElementById('newProjectBtn');
        if (newProjectBtn) {
            newProjectBtn.addEventListener('click', () => this.showCreateProjectModal());
        }

        // Projects list container (event delegation)
        const projectsList = document.getElementById('projectsList');
        if (projectsList) {
            projectsList.addEventListener('click', (e) => {
                const projectItem = e.target.closest('.project-item');
                if (!projectItem) return;

                const projectId = projectItem.dataset.projectId;
                const action = e.target.closest('[data-action]')?.dataset.action;

                if (action === 'edit') {
                    this.showEditProjectModal(projectId);
                } else if (action === 'delete') {
                    this.deleteProject(projectId);
                } else if (action === 'export') {
                    this.exportProject(projectId);
                } else if (!action) {
                    // Click on project item itself - activate project
                    this.activateProject(projectId);
                }
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+P: New project
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                this.showCreateProjectModal();
            }
        });
    }

    /**
     * Create a new project
     * @param {object} projectData - Project information
     * @returns {string} Project ID
     */
    async createProject(projectData) {
        const projectId = this.generateProjectId();
        
        const project = {
            id: projectId,
            name: projectData.name,
            description: projectData.description || '',
            color: projectData.color || this.getRandomColor(),
            icon: projectData.icon || '📁',
            created: Date.now(),
            updated: Date.now(),
            chatIds: [],
            sharedContext: {
                keywords: [],
                learnings: [],
                references: [],
                goals: []
            },
            settings: {
                autoAddChats: false,
                shareMemory: true,
                autoSummarize: false
            },
            statistics: {
                totalChats: 0,
                totalMessages: 0,
                lastActivity: Date.now()
            }
        };

        this.projects.set(projectId, project);
        await this.saveProjects();
        
        this.renderProjectsList();
        this.activateProject(projectId);
        
        console.log(`Created project: ${project.name}`);
        return projectId;
    }

    /**
     * Update project information
     * @param {string} projectId - Project ID
     * @param {object} updates - Fields to update
     */
    async updateProject(projectId, updates) {
        const project = this.projects.get(projectId);
        if (!project) {
            console.error(`Project ${projectId} not found`);
            return;
        }

        // Update fields
        Object.keys(updates).forEach(key => {
            if (key !== 'id' && key !== 'created') {
                project[key] = updates[key];
            }
        });

        project.updated = Date.now();
        
        await this.saveProjects();
        this.renderProjectsList();
        
        console.log(`Updated project: ${project.name}`);
    }

    /**
     * Delete a project
     * @param {string} projectId - Project ID
     */
    async deleteProject(projectId) {
        const project = this.projects.get(projectId);
        if (!project) return;

        if (!confirm(`Delete project "${project.name}"?\n\nChats will be moved to "No Project".`)) {
            return;
        }

        // Remove project from all chats
        project.chatIds.forEach(chatId => {
            const chat = this.chatManager.getChat(chatId);
            if (chat) {
                delete chat.projectId;
            }
        });

        this.projects.delete(projectId);
        
        if (this.activeProjectId === projectId) {
            this.activeProjectId = null;
        }

        await this.saveProjects();
        this.renderProjectsList();
        
        console.log(`Deleted project: ${project.name}`);
    }

    /**
     * Activate a project (set as current)
     * @param {string} projectId - Project ID
     */
    async activateProject(projectId) {
        if (projectId === this.activeProjectId) {
            // Deactivate if clicking same project
            this.activeProjectId = null;
            this.renderProjectsList();
            this.chatManager.filterChatsByProject(null);
            return;
        }

        const project = this.projects.get(projectId);
        if (!project) return;

        this.activeProjectId = projectId;
        
        // Update statistics
        project.statistics.lastActivity = Date.now();
        
        // Save active project
        localStorage.setItem('activeProjectId', projectId);
        
        // Filter chats by project
        this.chatManager.filterChatsByProject(projectId);
        
        // Update UI
        this.renderProjectsList();
        
        // Load shared context
        await this.loadProjectContext(projectId);
        
        console.log(`Activated project: ${project.name}`);
    }

    /**
     * Add chat to project
     * @param {string} chatId - Chat ID
     * @param {string} projectId - Project ID
     */
    async addChatToProject(chatId, projectId) {
        const project = this.projects.get(projectId);
        if (!project) {
            console.error(`Project ${projectId} not found`);
            return;
        }

        // Remove from old project if exists
        const chat = this.chatManager.getChat(chatId);
        if (chat && chat.projectId) {
            await this.removeChatFromProject(chatId, chat.projectId);
        }

        // Add to new project
        if (!project.chatIds.includes(chatId)) {
            project.chatIds.push(chatId);
            project.statistics.totalChats = project.chatIds.length;
        }

        // Update chat
        if (chat) {
            chat.projectId = projectId;
        }

        project.updated = Date.now();
        await this.saveProjects();
        
        console.log(`Added chat to project: ${project.name}`);
    }

    /**
     * Remove chat from project
     * @param {string} chatId - Chat ID
     * @param {string} projectId - Project ID
     */
    async removeChatFromProject(chatId, projectId) {
        const project = this.projects.get(projectId);
        if (!project) return;

        const index = project.chatIds.indexOf(chatId);
        if (index > -1) {
            project.chatIds.splice(index, 1);
            project.statistics.totalChats = project.chatIds.length;
        }

        // Update chat
        const chat = this.chatManager.getChat(chatId);
        if (chat) {
            delete chat.projectId;
        }

        project.updated = Date.now();
        await this.saveProjects();
    }

    /**
     * Load project context (shared learning)
     * @param {string} projectId - Project ID
     */
    async loadProjectContext(projectId) {
        const project = this.projects.get(projectId);
        if (!project) return;

        // Load shared context into memory manager
        if (this.memoryManager && project.settings.shareMemory) {
            const context = project.sharedContext;
            
            // Apply keywords
            if (context.keywords.length > 0) {
                console.log(`Loaded ${context.keywords.length} project keywords`);
            }
            
            // Apply learnings
            if (context.learnings.length > 0) {
                console.log(`Loaded ${context.learnings.length} project learnings`);
            }
        }

        return project.sharedContext;
    }

    /**
     * Add shared learning to project
     * @param {string} projectId - Project ID
     * @param {string} type - Type of learning (keyword, learning, reference, goal)
     * @param {any} data - Learning data
     */
    async addSharedLearning(projectId, type, data) {
        const project = this.projects.get(projectId);
        if (!project) return;

        const validTypes = ['keywords', 'learnings', 'references', 'goals'];
        if (!validTypes.includes(type)) {
            console.error(`Invalid learning type: ${type}`);
            return;
        }

        if (!project.sharedContext[type]) {
            project.sharedContext[type] = [];
        }

        project.sharedContext[type].push({
            data,
            added: Date.now(),
            addedBy: 'user' // Could track which chat added it
        });

        project.updated = Date.now();
        await this.saveProjects();
        
        console.log(`Added ${type} to project: ${project.name}`);
    }

    /**
     * Get all chats in a project
     * @param {string} projectId - Project ID
     * @returns {array} Array of chat objects
     */
    getProjectChats(projectId) {
        const project = this.projects.get(projectId);
        if (!project) return [];

        return project.chatIds
            .map(chatId => this.chatManager.getChat(chatId))
            .filter(chat => chat !== null);
    }

    /**
     * Get project by ID
     * @param {string} projectId - Project ID
     * @returns {object|null} Project object
     */
    getProject(projectId) {
        return this.projects.get(projectId) || null;
    }

    /**
     * Get all projects
     * @returns {array} Array of project objects
     */
    getAllProjects() {
        return Array.from(this.projects.values());
    }

    /**
     * Get active project
     * @returns {object|null} Active project object
     */
    getActiveProject() {
        return this.activeProjectId ? this.projects.get(this.activeProjectId) : null;
    }

    /**
     * Render projects list in sidebar
     */
    renderProjectsList() {
        const projectsList = document.getElementById('projectsList');
        if (!projectsList) return;

        const projects = this.getAllProjects();
        
        if (projects.length === 0) {
            projectsList.innerHTML = `
                <div class="empty-state">
                    <p>No projects yet</p>
                    <p class="empty-state-hint">Create one to organize your chats</p>
                </div>
            `;
            return;
        }

        // Sort by last activity
        projects.sort((a, b) => b.statistics.lastActivity - a.statistics.lastActivity);

        projectsList.innerHTML = projects.map(project => {
            const isActive = project.id === this.activeProjectId;
            const chatCount = project.chatIds.length;
            
            return `
                <div class="project-item ${isActive ? 'active' : ''}" data-project-id="${project.id}">
                    <div class="project-icon" style="background-color: ${project.color}">
                        ${project.icon}
                    </div>
                    <div class="project-info">
                        <div class="project-name">${this.escapeHtml(project.name)}</div>
                        <div class="project-stats">
                            <span class="project-chat-count">${chatCount} chat${chatCount !== 1 ? 's' : ''}</span>
                            ${project.description ? `<span class="project-description-preview">${this.escapeHtml(this.truncate(project.description, 30))}</span>` : ''}
                        </div>
                    </div>
                    <div class="project-actions">
                        <button class="project-action-btn" data-action="edit" title="Edit project">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                        </button>
                        <button class="project-action-btn" data-action="delete" title="Delete project">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Show create project modal
     */
    showCreateProjectModal() {
        const modal = this.createProjectModal('create');
        document.body.appendChild(modal);
        
        // Animate in
        setTimeout(() => modal.classList.add('show'), 10);
        
        // Focus name input
        const nameInput = modal.querySelector('#projectName');
        if (nameInput) nameInput.focus();
    }

    /**
     * Show edit project modal
     * @param {string} projectId - Project ID
     */
    showEditProjectModal(projectId) {
        const project = this.projects.get(projectId);
        if (!project) return;

        const modal = this.createProjectModal('edit', project);
        document.body.appendChild(modal);
        
        setTimeout(() => modal.classList.add('show'), 10);
    }

    /**
     * Create project modal
     * @param {string} mode - 'create' or 'edit'
     * @param {object} project - Project data (for edit mode)
     * @returns {HTMLElement} Modal element
     */
    createProjectModal(mode, project = null) {
        const isEdit = mode === 'edit';
        const modal = document.createElement('div');
        modal.className = 'project-modal';
        
        const colors = ['#10A37F', '#6366F1', '#EC4899', '#F59E0B', '#8B5CF6', '#EF4444', '#06B6D4', '#84CC16'];
        const icons = ['📁', '💼', '🎯', '🚀', '💡', '🔬', '🎨', '📊', '🧪', '⚡'];

        modal.innerHTML = `
            <div class="project-modal-content">
                <div class="project-modal-header">
                    <h3>${isEdit ? 'Edit Project' : 'Create New Project'}</h3>
                    <button class="project-modal-close">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                
                <form class="project-form" id="projectForm">
                    <div class="form-group">
                        <label for="projectName">Project Name *</label>
                        <input type="text" id="projectName" name="name" 
                               value="${isEdit ? this.escapeHtml(project.name) : ''}" 
                               placeholder="My Awesome Project" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="projectDescription">Description</label>
                        <textarea id="projectDescription" name="description" 
                                  placeholder="What is this project about?"
                                  rows="3">${isEdit ? this.escapeHtml(project.description) : ''}</textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Icon</label>
                        <div class="icon-picker" id="iconPicker">
                            ${icons.map(icon => `
                                <button type="button" class="icon-option ${isEdit && project.icon === icon ? 'selected' : ''}" 
                                        data-icon="${icon}">${icon}</button>
                            `).join('')}
                        </div>
                        <input type="hidden" id="projectIcon" name="icon" value="${isEdit ? project.icon : icons[0]}">
                    </div>
                    
                    <div class="form-group">
                        <label>Color</label>
                        <div class="color-picker" id="colorPicker">
                            ${colors.map(color => `
                                <button type="button" class="color-option ${isEdit && project.color === color ? 'selected' : ''}" 
                                        data-color="${color}" 
                                        style="background-color: ${color}"></button>
                            `).join('')}
                        </div>
                        <input type="hidden" id="projectColor" name="color" value="${isEdit ? project.color : colors[0]}">
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="btn-secondary" id="cancelBtn">Cancel</button>
                        <button type="submit" class="btn-primary">
                            ${isEdit ? 'Save Changes' : 'Create Project'}
                        </button>
                    </div>
                </form>
            </div>
        `;

        // Setup event listeners
        this.setupModalListeners(modal, mode, project?.id);

        return modal;
    }

    /**
     * Setup modal event listeners
     * @param {HTMLElement} modal - Modal element
     * @param {string} mode - 'create' or 'edit'
     * @param {string} projectId - Project ID (for edit mode)
     */
    setupModalListeners(modal, mode, projectId) {
        // Close button
        modal.querySelector('.project-modal-close').addEventListener('click', () => {
            this.closeModal(modal);
        });

        // Cancel button
        modal.querySelector('#cancelBtn').addEventListener('click', () => {
            this.closeModal(modal);
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal(modal);
            }
        });

        // Icon picker
        modal.querySelectorAll('.icon-option').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.icon-option').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                modal.querySelector('#projectIcon').value = btn.dataset.icon;
            });
        });

        // Color picker
        modal.querySelectorAll('.color-option').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.color-option').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                modal.querySelector('#projectColor').value = btn.dataset.color;
            });
        });

        // Form submit
        modal.querySelector('#projectForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
                icon: formData.get('icon'),
                color: formData.get('color')
            };

            if (mode === 'create') {
                await this.createProject(data);
            } else {
                await this.updateProject(projectId, data);
            }

            this.closeModal(modal);
        });
    }

    /**
     * Close modal
     * @param {HTMLElement} modal - Modal element
     */
    closeModal(modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }

    /**
     * Export project data
     * @param {string} projectId - Project ID
     * @returns {object} Project data
     */
    exportProject(projectId) {
        const project = this.projects.get(projectId);
        if (!project) return null;

        const chats = this.getProjectChats(projectId);
        
        const exportData = {
            ...project,
            chats: chats.map(chat => ({
                id: chat.id,
                title: chat.title,
                messages: chat.messages,
                created: chat.created,
                updated: chat.updated
            }))
        };

        // Download as JSON
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `project_${project.name}_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);

        console.log(`Exported project: ${project.name}`);
        return exportData;
    }

    /**
     * Import project data
     * @param {object} data - Project data
     */
    async importProject(data) {
        if (!data || !data.name) {
            console.error('Invalid project data');
            return;
        }

        // Create new project with imported data
        const projectId = await this.createProject({
            name: data.name + ' (Imported)',
            description: data.description,
            icon: data.icon,
            color: data.color
        });

        const project = this.projects.get(projectId);
        
        // Import shared context
        if (data.sharedContext) {
            project.sharedContext = data.sharedContext;
        }

        // Import chats if available
        if (data.chats && Array.isArray(data.chats)) {
            // This would need chat manager support
            console.log(`Project has ${data.chats.length} chats to import`);
        }

        await this.saveProjects();
        console.log(`Imported project: ${project.name}`);
    }

    /**
     * Save projects to storage
     */
    async saveProjects() {
        try {
            const data = {
                projects: Array.from(this.projects.entries()).map(([id, project]) => ({
                    ...project
                })),
                activeProjectId: this.activeProjectId
            };

            localStorage.setItem('projects', JSON.stringify(data));
        } catch (error) {
            console.error('Failed to save projects:', error);
        }
    }

    /**
     * Load projects from storage
     */
    async loadProjects() {
        try {
            const data = localStorage.getItem('projects');
            if (!data) return;

            const parsed = JSON.parse(data);
            
            if (parsed.projects && Array.isArray(parsed.projects)) {
                parsed.projects.forEach(project => {
                    this.projects.set(project.id, project);
                });
            }

            if (parsed.activeProjectId) {
                this.activeProjectId = parsed.activeProjectId;
            }

            console.log(`Loaded ${this.projects.size} projects`);
        } catch (error) {
            console.error('Failed to load projects:', error);
        }
    }

    /**
     * Generate unique project ID
     * @returns {string} Project ID
     */
    generateProjectId() {
        return `proj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get random color from palette
     * @returns {string} Color hex code
     */
    getRandomColor() {
        const colors = ['#10A37F', '#6366F1', '#EC4899', '#F59E0B', '#8B5CF6', '#EF4444', '#06B6D4', '#84CC16'];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    /**
     * Escape HTML
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Truncate text
     * @param {string} text - Text to truncate
     * @param {number} length - Maximum length
     * @returns {string} Truncated text
     */
    truncate(text, length) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    }

    /**
     * Get statistics about projects
     * @returns {object} Statistics
     */
    getStatistics() {
        const projects = this.getAllProjects();
        
        let totalChats = 0;
        let totalMessages = 0;
        
        projects.forEach(project => {
            totalChats += project.statistics.totalChats;
            totalMessages += project.statistics.totalMessages;
        });

        return {
            totalProjects: projects.length,
            totalChats,
            totalMessages,
            averageChatsPerProject: totalChats / Math.max(projects.length, 1),
            activeProject: this.getActiveProject()?.name || 'None'
        };
    }
}
