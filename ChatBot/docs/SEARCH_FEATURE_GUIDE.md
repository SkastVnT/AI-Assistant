# 🔍 Search Feature Usage Guide

## Quick Start

### Activate Search
- **Click** the search input in the sidebar
- **Or press** `Ctrl+F` anywhere in the app

### Perform Search
1. Type your search query
2. Wait 300ms (debounced)
3. See results appear instantly

### Navigate Results
- Click any result to load that chat
- See highlighted matches in yellow
- View match badges (TITLE/CONTENT)

### Clear Search
- **Click** the X button in results header
- **Or press** `ESC` key

---

## Visual Guide

```
┌─────────────────────────────────────┐
│  SIDEBAR                            │
├─────────────────────────────────────┤
│  🔍 Search...          [Ctrl+F]     │  ← Search Input
├─────────────────────────────────────┤
│  📊 Found 3 results for "AI"    [×] │  ← Results Header
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐  │
│  │ AI Project Ideas         [TITLE]│  ← Title Match Badge (Green)
│  │ ...discussing AI tools...      │  ← Snippet with highlight
│  │ 3 matches • 2h ago             │  ← Metadata
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Python Tutorial     [CONTENT]  │  ← Content Match Badge (Purple)
│  │ ...using AI for code...        │
│  │ 1 match • Yesterday            │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Machine Learning    [CONTENT]  │
│  │ ...AI models and AI agents...  │
│  │ 2 matches • Last week          │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Features Breakdown

### 1. Real-Time Search
```javascript
Type: "machine learning"
  ↓ 300ms debounce
Search executes
  ↓
Results displayed instantly
```

**Benefits**:
- No lag while typing
- Instant feedback
- Smooth experience

---

### 2. Intelligent Scoring

**Priority Order**:
1. **Title Matches** (100 points) - Most relevant
2. **Multiple Content Matches** (10+ points per match)
3. **Single Content Matches** (10 points)

**Example Ranking**:
```
1. "AI Tools" (title)          → Score: 100
2. "AI AI AI" (3 content)      → Score: 30
3. "About AI" (1 content)      → Score: 10
```

---

### 3. Visual Highlighting

**Highlighted Text**:
```
Normal text discussing machine learning concepts...
        ↓
Normal text discussing [machine learning] concepts...
                      └─── Yellow highlight ───┘
```

**Match Badges**:
- 🟢 **TITLE** = Found in chat title (green badge)
- 🔵 **CONTENT** = Found in messages (purple badge)

---

### 4. Contextual Snippets

**Long Message**:
```
"The history of artificial intelligence dates back to the 1950s 
when researchers first began exploring how machines could simulate 
human intelligence. Today, AI has evolved significantly..."
```

**Search: "AI"**
```
"...began exploring how machines could simulate human intelligence. 
Today, AI has evolved..."
  └── Context before/after match ──┘
```

---

### 5. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search input |
| `ESC` | Clear search & return to chat list |
| `Enter` | (Future) Jump to next match |

---

## Search Tips

### Basic Search
```
Query: "python"
Finds: python, Python, PYTHON (case-insensitive)
```

### Multiple Words
```
Query: "machine learning"
Finds: Chats containing both "machine" AND "learning"
```

### Partial Matches
```
Query: "learn"
Finds: learn, learning, learned, learner
```

---

## Advanced Features (Future)

### Date Filters
```javascript
searchHandler.advancedSearch("AI", {
    dateFrom: "2024-01-01",
    dateTo: "2024-12-31"
});
```

### Model Filters
```javascript
searchHandler.advancedSearch("code", {
    models: ["gpt-4", "claude-3"]
});
```

### Length Filters
```javascript
searchHandler.advancedSearch("tutorial", {
    minMessages: 10,
    maxMessages: 50
});
```

---

## UI States

### 1. Empty State (No Results)
```
┌─────────────────────────────────┐
│     🔍                          │
│                                 │
│  No results found               │
│  Try different keywords         │
│                                 │
└─────────────────────────────────┘
```

### 2. Loading State (Future)
```
┌─────────────────────────────────┐
│  🔄 Searching...                │
└─────────────────────────────────┘
```

### 3. Results State
```
┌─────────────────────────────────┐
│  📊 Found 5 results         [×] │
│                                 │
│  [Result 1]                     │
│  [Result 2]                     │
│  [Result 3]                     │
│  ...                            │
└─────────────────────────────────┘
```

---

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Debounce Time | 300ms | Optimal for typing |
| Search Speed | <50ms | For 100 chats |
| Max Results | Unlimited | All matches shown |
| Snippet Length | ~100 chars | Context around match |

---

## Code Examples

### Basic Usage
```javascript
// Focus search
document.querySelector('#searchInput').focus();

// Perform search
searchHandler.performSearch('machine learning');

// Clear search
searchHandler.clearSearch();
```

### Listen for Results
```javascript
searchHandler.on('results', (results) => {
    console.log(`Found ${results.length} results`);
});
```

### Custom Filtering
```javascript
const results = searchHandler.searchChats('AI', {
    titleOnly: true,
    minScore: 50
});
```

---

## Troubleshooting

### Search Not Working?
1. Check console for errors
2. Verify searchHandler is initialized
3. Check DOM elements exist (#searchInput, #chatList)

### No Results Showing?
1. Verify chat data is loaded
2. Check search query (case-insensitive)
3. Try broader keywords

### Highlighting Not Working?
1. Check CSS file loaded (style_chatgpt_v2.css)
2. Verify `<mark>` styles defined
3. Check browser supports HTML5

---

## Accessibility

### Keyboard Navigation
- ✅ Full keyboard support
- ✅ Focus management
- ✅ Screen reader friendly

### Visual Feedback
- ✅ Clear contrast ratios
- ✅ Color not sole indicator
- ✅ Text alternatives

### Responsive Design
- ✅ Mobile-friendly
- ✅ Touch-friendly targets
- ✅ Adaptive layout

---

## Related Documentation

- [PHASE2_COMPLETE_SUMMARY.md](./PHASE2_COMPLETE_SUMMARY.md) - Technical details
- [CHATGPT_UPGRADE_PLAN.md](./CHATGPT_UPGRADE_PLAN.md) - Overall project plan
- [HUONG_DAN_GIAO_DIEN_MOI.md](./HUONG_DAN_GIAO_DIEN_MOI.md) - Vietnamese guide

---

## Changelog

### v1.0 (Phase 2 Complete)
- ✅ Real-time search with debouncing
- ✅ Intelligent relevance scoring
- ✅ Visual highlighting
- ✅ Keyboard shortcuts
- ✅ Contextual snippets
- ✅ Match badges
- ✅ Dark mode support

### Future Enhancements
- [ ] Advanced filters (date, model, length)
- [ ] Search history
- [ ] Regex support
- [ ] Export results
- [ ] Search within chat

---

*Last updated: January 2025*  
*Part of ChatGPT V2 Interface Project*
