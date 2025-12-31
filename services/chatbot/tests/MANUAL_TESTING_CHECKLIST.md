# Manual Testing Checklist - Phase 5

## User Acceptance Testing (UAT) Checklist

### 1. Conversation Management

#### 1.1 Create New Conversation
- [ ] Click "New Chat" button
- [ ] Verify new conversation appears in sidebar
- [ ] Verify conversation has default title
- [ ] Verify timestamp is correct

#### 1.2 Send Messages
- [ ] Type message and press Enter
- [ ] Verify message appears in chat
- [ ] Verify AI response is received
- [ ] Verify messages are in correct order
- [ ] Verify timestamps are displayed

#### 1.3 Edit Messages
- [ ] Click edit button on user message
- [ ] Modify message content
- [ ] Click save
- [ ] Verify message is updated
- [ ] Verify "(edited)" indicator appears

#### 1.4 Delete Messages
- [ ] Click delete button on message
- [ ] Confirm deletion
- [ ] Verify message is removed
- [ ] Verify conversation still works

#### 1.5 Conversation History
- [ ] Create multiple conversations
- [ ] Switch between conversations
- [ ] Verify correct messages load
- [ ] Verify no data mixing

---

### 2. Search & Filter

#### 2.1 Search Conversations
- [ ] Use search box
- [ ] Search by title
- [ ] Search by message content
- [ ] Verify relevant results appear
- [ ] Verify no false positives

#### 2.2 Filter by Date
- [ ] Filter by today
- [ ] Filter by this week
- [ ] Filter by this month
- [ ] Verify correct conversations shown

---

### 3. AI Memory System

#### 3.1 Memory Storage
- [ ] Have conversation about a topic
- [ ] Verify memory is saved
- [ ] Start new conversation
- [ ] Reference previous topic
- [ ] Verify AI remembers

#### 3.2 Memory Search
- [ ] Search memories by keyword
- [ ] Verify relevant memories found
- [ ] Verify memory importance ranking

---

### 4. Model Selection

#### 4.1 Change AI Model
- [ ] Switch from Grok to Gemini
- [ ] Verify conversation uses new model
- [ ] Switch to Grok-3
- [ ] Verify response style changes

#### 4.2 Model-Specific Features
- [ ] Test image generation (if supported)
- [ ] Test code generation
- [ ] Test long conversations

---

### 5. File Handling

#### 5.1 Upload Files
- [ ] Upload text file
- [ ] Upload image
- [ ] Upload PDF
- [ ] Verify files are processed

#### 5.2 File Analysis
- [ ] Ask questions about uploaded file
- [ ] Verify AI can access file content

---

### 6. Error Handling

#### 6.1 Network Errors
- [ ] Disconnect network
- [ ] Try to send message
- [ ] Verify error message shown
- [ ] Reconnect network
- [ ] Verify recovery works

#### 6.2 Invalid Input
- [ ] Send empty message
- [ ] Send very long message (>10000 chars)
- [ ] Send special characters
- [ ] Verify appropriate handling

---

### 7. Performance Checks

#### 7.1 Response Time
- [ ] Send simple query
- [ ] Response within 3 seconds: ____
- [ ] Send complex query
- [ ] Response within 10 seconds: ____

#### 7.2 UI Responsiveness
- [ ] Scrolling is smooth
- [ ] No lag when typing
- [ ] Sidebar updates quickly

#### 7.3 Memory Usage
- [ ] Check browser memory usage
- [ ] After 1 hour usage: ____ MB
- [ ] No memory leaks observed

---

### 8. Data Persistence

#### 8.1 Session Persistence
- [ ] Have conversation
- [ ] Refresh page
- [ ] Verify conversations remain
- [ ] Verify messages intact

#### 8.2 Cross-Device
- [ ] Login on different device
- [ ] Verify conversations sync
- [ ] Verify memories available

---

### 9. Security

#### 9.1 Authentication
- [ ] Login required to access
- [ ] Logout works properly
- [ ] Session expires correctly

#### 9.2 Data Isolation
- [ ] Cannot access other users' data
- [ ] API requires authentication

---

### 10. Edge Cases

#### 10.1 Special Scenarios
- [ ] Very long conversation (100+ messages)
- [ ] Rapid message sending
- [ ] Multiple tabs open
- [ ] Browser back/forward buttons

---

## Test Results Summary

| Category | Pass | Fail | Notes |
|----------|------|------|-------|
| Conversation Management | | | |
| Search & Filter | | | |
| AI Memory System | | | |
| Model Selection | | | |
| File Handling | | | |
| Error Handling | | | |
| Performance | | | |
| Data Persistence | | | |
| Security | | | |
| Edge Cases | | | |

**Total Pass:** ____  
**Total Fail:** ____  
**Pass Rate:** ____%

---

## Tester Information

- **Tester Name:** _________________
- **Date:** _________________
- **Environment:** 
  - Browser: _________________
  - OS: _________________
  - Version: _________________

## Notes & Issues Found

1. _________________________________________________
2. _________________________________________________
3. _________________________________________________

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues
- [ ] Ready for deployment

**Signature:** _________________  
**Date:** _________________
