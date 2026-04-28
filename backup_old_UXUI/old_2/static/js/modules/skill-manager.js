/**
 * Skill Manager Module
 * Manages runtime skill selection: fetch skills, activate/deactivate, update UI.
 * Skills are session-level (server-side binding via /api/skills/activate).
 */

export class SkillManager {
    constructor() {
        this.skills = [];
        this.activeSkillId = null;
        this.activeSkill = null;
        this.initialized = false;
        this._dropdownOpen = false;
    }

    /**
     * Initialize: fetch skills, sync active state, render dropdown, bind events.
     */
    async init() {
        try {
            await this.loadSkills();
            await this.syncActiveSkill();
            this.renderDropdown();
            this.setupEventListeners();
            this.updateUI();
            this.initialized = true;
            console.log('[SkillManager] Initialized with', this.skills.length, 'skills');
        } catch (err) {
            console.warn('[SkillManager] Init failed:', err.message);
        }
    }

    /**
     * Fetch available skills from the backend.
     */
    async loadSkills() {
        const res = await fetch('/api/skills');
        if (!res.ok) throw new Error(`Failed to load skills: ${res.status}`);
        const data = await res.json();
        this.skills = (data.skills || []).filter(s => s.enabled !== false);
    }

    /**
     * Sync with server to get the currently active skill for this session.
     */
    async syncActiveSkill() {
        const res = await fetch('/api/skills/active');
        if (!res.ok) return;
        const data = await res.json();
        if (data.active && data.skill_id) {
            this.activeSkillId = data.skill_id;
            this.activeSkill = this.skills.find(s => s.id === data.skill_id) || null;
        } else {
            this.activeSkillId = null;
            this.activeSkill = null;
        }
    }

    /**
     * Activate a skill by ID.
     */
    async activate(skillId) {
        try {
            const res = await fetch('/api/skills/activate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ skill_id: skillId }),
            });
            if (!res.ok) throw new Error(`Activate failed: ${res.status}`);
            const data = await res.json();
            if (data.success) {
                this.activeSkillId = data.skill_id;
                this.activeSkill = this.skills.find(s => s.id === data.skill_id) || null;
                this.updateUI();
                console.log('[SkillManager] Activated:', data.skill_id);
            }
        } catch (err) {
            console.error('[SkillManager] Activate error:', err.message);
        }
    }

    /**
     * Deactivate the current skill.
     */
    async deactivate() {
        try {
            await fetch('/api/skills/deactivate', { method: 'POST' });
            this.activeSkillId = null;
            this.activeSkill = null;
            this.updateUI();
            console.log('[SkillManager] Deactivated');
        } catch (err) {
            console.error('[SkillManager] Deactivate error:', err.message);
        }
    }

    /**
     * Get the active skill ID (for external use).
     */
    getActiveSkillId() {
        return this.activeSkillId;
    }

    /**
     * Show an auto-routed skill indicator (temporary, does not persist to session).
     * Called from SSE metadata when skill_source === "auto".
     */
    showAutoRouted(skillId, skillName, keywords) {
        this._autoRouted = { skillId, skillName, keywords: keywords || [] };
        const badge = document.getElementById('activeSkillBadge');
        if (badge) {
            const kwText = this._autoRouted.keywords.length > 0
                ? ` (${this._autoRouted.keywords.join(', ')})`
                : '';
            badge.innerHTML = `⚡ ${this._escapeHtml(skillName)}${this._escapeHtml(kwText)} <button class="skill-badge__clear skill-badge__clear--auto" title="Dismiss">&times;</button>`;
            badge.classList.add('auto-routed');
            badge.style.display = '';
            const clearBtn = badge.querySelector('.skill-badge__clear--auto');
            if (clearBtn) {
                clearBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.clearAutoRouted();
                });
            }
        }
        console.log('[SkillManager] Auto-routed to:', skillName, keywords);
    }

    /**
     * Clear the auto-routed skill indicator.
     */
    clearAutoRouted() {
        this._autoRouted = null;
        const badge = document.getElementById('activeSkillBadge');
        if (badge) {
            badge.classList.remove('auto-routed');
            // Restore manual skill badge if one is active, otherwise hide
            this._updateBadge();
        }
    }

    /**
     * Populate the skill dropdown with items fetched from the API.
     */
    renderDropdown() {
        const container = document.getElementById('skillListContainer');
        if (!container) return;

        container.innerHTML = '';

        if (this.skills.length === 0) {
            container.innerHTML = '<div style="padding: 12px 16px; color: var(--text-tertiary); font-size: 12px;">No skills available</div>';
            return;
        }

        // Group skills by tags
        const tagged = {};
        const untagged = [];
        this.skills.forEach(skill => {
            if (skill.tags && skill.tags.length > 0) {
                const tag = skill.tags[0];
                if (!tagged[tag]) tagged[tag] = [];
                tagged[tag].push(skill);
            } else {
                untagged.push(skill);
            }
        });

        const renderSkillItem = (skill) => {
            const isActive = this.activeSkillId === skill.id;
            const item = document.createElement('div');
            item.className = 'skill-option model-dropdown__item' + (isActive ? ' active' : '');
            item.dataset.skillId = skill.id;
            item.innerHTML = `
                <span class="model-dropdown__item-icon">${this._getSkillIcon(skill)}</span>
                <div class="model-dropdown__item-info">
                    <div class="model-dropdown__item-name">${this._escapeHtml(skill.name)}</div>
                    <div class="model-dropdown__item-desc">${this._escapeHtml(skill.description || '')}</div>
                </div>
                ${skill.default_model ? `<span class="model-dropdown__item-badge pro">${this._escapeHtml(skill.default_model)}</span>` : ''}
            `;
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this._selectSkill(skill.id);
            });
            return item;
        };

        // Render grouped skills
        for (const [tag, skills] of Object.entries(tagged)) {
            const group = document.createElement('div');
            group.className = 'model-dropdown__group';
            group.innerHTML = `<div class="model-dropdown__group-label">${this._escapeHtml(tag)}</div>`;
            skills.forEach(s => group.appendChild(renderSkillItem(s)));
            container.appendChild(group);
        }

        // Render untagged skills
        if (untagged.length > 0) {
            const group = document.createElement('div');
            group.className = 'model-dropdown__group';
            if (Object.keys(tagged).length > 0) {
                group.innerHTML = '<div class="model-dropdown__group-label">Other</div>';
            }
            untagged.forEach(s => group.appendChild(renderSkillItem(s)));
            container.appendChild(group);
        }
    }

    /**
     * Setup click handlers for the skill selector button and dropdown.
     */
    setupEventListeners() {
        const btn = document.getElementById('skillSelectorBtn');
        const dropdown = document.getElementById('skillSelectorDropdown');
        if (!btn || !dropdown) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            this._dropdownOpen = !this._dropdownOpen;
            if (this._dropdownOpen) {
                dropdown.classList.remove('hidden');
                dropdown.classList.add('open');
            } else {
                dropdown.classList.add('hidden');
                dropdown.classList.remove('open');
            }
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!btn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
                dropdown.classList.remove('open');
                this._dropdownOpen = false;
            }
        });

        // "None" option
        const noneOption = document.getElementById('skillNoneOption');
        if (noneOption) {
            noneOption.addEventListener('click', (e) => {
                e.stopPropagation();
                this._selectSkill(null);
            });
        }
    }

    /**
     * Handle skill selection (activate or deactivate).
     */
    async _selectSkill(skillId) {
        const dropdown = document.getElementById('skillSelectorDropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
            dropdown.classList.remove('open');
            this._dropdownOpen = false;
        }

        if (skillId && skillId !== this.activeSkillId) {
            await this.activate(skillId);
        } else if (!skillId && this.activeSkillId) {
            await this.deactivate();
        }

        // Update dropdown active states
        document.querySelectorAll('.skill-option').forEach(el => {
            const isNone = el.id === 'skillNoneOption';
            const elSkillId = el.dataset.skillId;
            if (!skillId && isNone) {
                el.classList.add('active');
            } else if (skillId && elSkillId === skillId) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
    }

    /**
     * Update all UI elements to reflect the current skill state.
     */
    updateUI() {
        this._updateButton();
        this._updateBadge();
        this._updateHiddenInput();
        this._updateDropdownActiveState();
    }

    _updateButton() {
        const label = document.getElementById('skillSelectorLabel');
        const icon = document.getElementById('skillSelectorIcon');
        const btn = document.getElementById('skillSelectorBtn');
        if (!label) return;

        if (this.activeSkill) {
            label.textContent = this.activeSkill.name;
            if (btn) btn.classList.add('skill-active');
        } else {
            label.textContent = 'Skill';
            if (btn) btn.classList.remove('skill-active');
        }

        // Re-render lucide icon
        if (icon && window.lucide) {
            const iconName = this.activeSkill ? 'book-marked' : 'book-open';
            icon.innerHTML = '<i data-lucide="' + iconName + '" class="lucide"></i>';
            lucide.createIcons({ nodes: [icon] });
        }
    }

    _updateBadge() {
        const badge = document.getElementById('activeSkillBadge');
        if (!badge) return;

        if (this.activeSkill) {
            badge.innerHTML = `🎯 ${this._escapeHtml(this.activeSkill.name)} <button class="skill-badge__clear" title="Clear skill">&times;</button>`;
            badge.style.display = '';
            const clearBtn = badge.querySelector('.skill-badge__clear');
            if (clearBtn) {
                clearBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._selectSkill(null);
                });
            }
        } else {
            badge.innerHTML = '';
            badge.style.display = 'none';
        }
    }

    _updateHiddenInput() {
        const input = document.getElementById('activeSkillId');
        if (input) input.value = this.activeSkillId || '';
    }

    _updateDropdownActiveState() {
        document.querySelectorAll('.skill-option').forEach(el => {
            const isNone = el.id === 'skillNoneOption';
            const elSkillId = el.dataset.skillId;
            if (!this.activeSkillId && isNone) {
                el.classList.add('active');
            } else if (this.activeSkillId && elSkillId === this.activeSkillId) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });
    }

    _getSkillIcon(skill) {
        const tagIcons = {
            'development': '💻',
            'writing': '✍️',
            'analysis': '📊',
            'creative': '🎨',
            'research': '🔬',
            'education': '📚',
            'productivity': '⚡',
        };
        if (skill.tags && skill.tags.length > 0) {
            for (const tag of skill.tags) {
                if (tagIcons[tag.toLowerCase()]) return tagIcons[tag.toLowerCase()];
            }
        }
        return '🎯';
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
