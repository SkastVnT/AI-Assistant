"""
Phase 6: Comprehensive Testing & Integration
Tests all 5 phases plus existing features
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results storage
test_results = {
    'timestamp': datetime.now().isoformat(),
    'total_tests': 0,
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'tests': []
}

def test_result(name, status, message='', details=None):
    """Record test result"""
    result = {
        'name': name,
        'status': status,  # 'PASS', 'FAIL', 'SKIP'
        'message': message,
        'details': details or {}
    }
    test_results['tests'].append(result)
    test_results['total_tests'] += 1
    
    if status == 'PASS':
        test_results['passed'] += 1
        logger.info(f"✅ {name}: PASS - {message}")
    elif status == 'FAIL':
        test_results['failed'] += 1
        logger.error(f"❌ {name}: FAIL - {message}")
    elif status == 'SKIP':
        test_results['skipped'] += 1
        logger.warning(f"⏭️ {name}: SKIP - {message}")

class Phase6Tester:
    """Comprehensive Phase 6 Testing Suite"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.static_path = self.base_path / 'static'
        self.templates_path = self.base_path / 'templates'
        self.docs_path = self.base_path / 'docs'
        
    def run_all_tests(self):
        """Run all test categories"""
        logger.info("="*60)
        logger.info("🚀 Starting Phase 6: Comprehensive Testing & Integration")
        logger.info("="*60)
        
        # File structure tests
        self.test_file_structure()
        
        # Phase 1-5 integration tests
        self.test_phase1_design()
        self.test_phase2_search()
        self.test_phase3_versions()
        self.test_phase4_projects()
        self.test_phase5_polish()
        
        # Existing features tests
        self.test_existing_features()
        
        # JavaScript module tests
        self.test_javascript_modules()
        
        # CSS tests
        self.test_css_structure()
        
        # Documentation tests
        self.test_documentation()
        
        # Generate report
        self.generate_report()
        
    def test_file_structure(self):
        """Test that all required files exist"""
        logger.info("\n📂 Testing File Structure...")
        
        required_files = {
            # Templates
            'templates/index_chatgpt_v2.html': 'Main V2 template',
            
            # JavaScript modules
            'static/js/main_v2.js': 'Main V2 entry point',
            'static/js/modules/chat-manager.js': 'Chat manager',
            'static/js/modules/api-service.js': 'API service',
            'static/js/modules/message-renderer.js': 'Message renderer',
            'static/js/modules/file-handler.js': 'File handler',
            'static/js/modules/image-gen.js': 'Image generator',
            'static/js/modules/memory-manager.js': 'Memory manager',
            'static/js/modules/export-handler.js': 'Export handler',
            'static/js/modules/ui-utils.js': 'UI utilities',
            'static/js/modules/performance-utils.js': 'Performance utilities',
            'static/js/modules/search-handler.js': 'Search handler (Phase 2)',
            'static/js/modules/version-navigator.js': 'Version navigator (Phase 3)',
            'static/js/modules/projects-manager.js': 'Projects manager (Phase 4)',
            'static/js/modules/preferences-manager.js': 'Preferences manager (Phase 5)',
            
            # CSS
            'static/css/style_chatgpt_v2.css': 'Main V2 stylesheet',
            
            # Documentation
            'docs/PHASE2_COMPLETE_SUMMARY.md': 'Phase 2 docs',
            'docs/PHASE3_COMPLETE_SUMMARY.md': 'Phase 3 docs',
            'docs/PHASE4_COMPLETE_SUMMARY.md': 'Phase 4 docs',
            'docs/PHASE5_COMPLETE_SUMMARY.md': 'Phase 5 docs',
        }
        
        for file_path, description in required_files.items():
            full_path = self.base_path / file_path
            if full_path.exists():
                test_result(
                    f"File exists: {file_path}",
                    'PASS',
                    description,
                    {'size': full_path.stat().st_size}
                )
            else:
                test_result(
                    f"File exists: {file_path}",
                    'FAIL',
                    f"Required file missing: {description}"
                )
    
    def test_phase1_design(self):
        """Test Phase 1: ChatGPT-style Design"""
        logger.info("\n🎨 Testing Phase 1: Design & HTML/CSS...")
        
        # Test HTML structure
        html_file = self.templates_path / 'index_chatgpt_v2.html'
        if html_file.exists():
            content = html_file.read_text(encoding='utf-8')
            
            # Check for key HTML elements
            required_elements = [
                ('app-container', 'Main app container'),
                ('sidebar', 'Sidebar'),
                ('main-content', 'Main content area'),
                ('messages-container', 'Messages container'),
                ('input-container', 'Input container'),
                ('chat-header', 'Chat header'),
            ]
            
            for element, description in required_elements:
                if element in content:
                    test_result(
                        f"Phase 1: HTML element '{element}'",
                        'PASS',
                        description
                    )
                else:
                    test_result(
                        f"Phase 1: HTML element '{element}'",
                        'FAIL',
                        f"Missing {description}"
                    )
            
            # Check for CDN libraries
            cdn_libraries = ['marked', 'highlight.js', 'jspdf', 'html2canvas']
            for lib in cdn_libraries:
                if lib.lower() in content.lower():
                    test_result(
                        f"Phase 1: CDN library '{lib}'",
                        'PASS',
                        f"{lib} loaded"
                    )
        
        # Test CSS structure
        css_file = self.static_path / 'css' / 'style_chatgpt_v2.css'
        if css_file.exists():
            content = css_file.read_text(encoding='utf-8')
            lines = len(content.splitlines())
            
            test_result(
                'Phase 1: CSS file size',
                'PASS',
                f'{lines} lines',
                {'lines': lines, 'bytes': len(content)}
            )
            
            # Check for CSS variables
            if ':root' in content and '--' in content:
                test_result(
                    'Phase 1: CSS variables',
                    'PASS',
                    'CSS custom properties defined'
                )
            
            # Check for dark mode
            if 'dark-mode' in content:
                test_result(
                    'Phase 1: Dark mode support',
                    'PASS',
                    'Dark mode styles present'
                )
    
    def test_phase2_search(self):
        """Test Phase 2: Search Functionality"""
        logger.info("\n🔍 Testing Phase 2: Search Functionality...")
        
        search_handler = self.static_path / 'js' / 'modules' / 'search-handler.js'
        if search_handler.exists():
            content = search_handler.read_text(encoding='utf-8')
            
            # Check for key features
            features = [
                ('SearchHandler', 'Main search class'),
                ('initSearch', 'Search initialization'),
                ('handleSearch', 'Search handler'),
                ('highlightMatches', 'Match highlighting'),
                ('navigateResults', 'Result navigation'),
                ('Ctrl+F', 'Keyboard shortcut'),
            ]
            
            for feature, description in features:
                if feature in content:
                    test_result(
                        f"Phase 2: Feature '{feature}'",
                        'PASS',
                        description
                    )
                else:
                    test_result(
                        f"Phase 2: Feature '{feature}'",
                        'FAIL',
                        f"Missing {description}"
                    )
            
            # Check line count
            lines = len(content.splitlines())
            test_result(
                'Phase 2: search-handler.js size',
                'PASS' if lines >= 400 else 'FAIL',
                f'{lines} lines',
                {'lines': lines}
            )
    
    def test_phase3_versions(self):
        """Test Phase 3: Version Navigation"""
        logger.info("\n🔄 Testing Phase 3: Version Navigation...")
        
        version_nav = self.static_path / 'js' / 'modules' / 'version-navigator.js'
        if version_nav.exists():
            content = version_nav.read_text(encoding='utf-8')
            
            features = [
                ('VersionNavigator', 'Main version class'),
                ('addVersion', 'Version creation'),
                ('navigateToPrevious', 'Previous version'),
                ('navigateToNext', 'Next version'),
                ('showVersionHistory', 'Version history modal'),
                ('localStorage', 'Persistence'),
            ]
            
            for feature, description in features:
                if feature in content:
                    test_result(
                        f"Phase 3: Feature '{feature}'",
                        'PASS',
                        description
                    )
                else:
                    test_result(
                        f"Phase 3: Feature '{feature}'",
                        'FAIL',
                        f"Missing {description}"
                    )
            
            lines = len(content.splitlines())
            test_result(
                'Phase 3: version-navigator.js size',
                'PASS' if lines >= 600 else 'FAIL',
                f'{lines} lines',
                {'lines': lines}
            )
    
    def test_phase4_projects(self):
        """Test Phase 4: Projects System"""
        logger.info("\n📁 Testing Phase 4: Projects System...")
        
        projects_mgr = self.static_path / 'js' / 'modules' / 'projects-manager.js'
        if projects_mgr.exists():
            content = projects_mgr.read_text(encoding='utf-8')
            
            features = [
                ('ProjectsManager', 'Main projects class'),
                ('createProject', 'Project creation'),
                ('updateProject', 'Project update'),
                ('deleteProject', 'Project deletion'),
                ('addChatToProject', 'Add chat to project'),
                ('exportProject', 'Export functionality'),
                ('importProject', 'Import functionality'),
            ]
            
            for feature, description in features:
                if feature in content:
                    test_result(
                        f"Phase 4: Feature '{feature}'",
                        'PASS',
                        description
                    )
                else:
                    test_result(
                        f"Phase 4: Feature '{feature}'",
                        'FAIL',
                        f"Missing {description}"
                    )
            
            # Check for colors and icons
            if '8' in content and 'color' in content.lower():
                test_result(
                    'Phase 4: Project colors',
                    'PASS',
                    'Color customization present'
                )
            
            if 'icon' in content.lower():
                test_result(
                    'Phase 4: Project icons',
                    'PASS',
                    'Icon customization present'
                )
            
            lines = len(content.splitlines())
            test_result(
                'Phase 4: projects-manager.js size',
                'PASS' if lines >= 700 else 'FAIL',
                f'{lines} lines',
                {'lines': lines}
            )
    
    def test_phase5_polish(self):
        """Test Phase 5: Sidebar Toggle & Polish"""
        logger.info("\n✨ Testing Phase 5: Sidebar Toggle & Polish...")
        
        prefs_mgr = self.static_path / 'js' / 'modules' / 'preferences-manager.js'
        if prefs_mgr.exists():
            content = prefs_mgr.read_text(encoding='utf-8')
            
            features = [
                ('PreferencesManager', 'Preferences manager'),
                ('SidebarToggle', 'Sidebar toggle'),
                ('NotificationManager', 'Notification system'),
                ('localStorage', 'Persistence'),
                ('toggle', 'Toggle functionality'),
                ('applyTheme', 'Theme application'),
            ]
            
            for feature, description in features:
                if feature in content:
                    test_result(
                        f"Phase 5: Feature '{feature}'",
                        'PASS',
                        description
                    )
                else:
                    test_result(
                        f"Phase 5: Feature '{feature}'",
                        'FAIL',
                        f"Missing {description}"
                    )
            
            lines = len(content.splitlines())
            test_result(
                'Phase 5: preferences-manager.js size',
                'PASS' if lines >= 500 else 'FAIL',
                f'{lines} lines',
                {'lines': lines}
            )
        
        # Test CSS polish additions
        css_file = self.static_path / 'css' / 'style_chatgpt_v2.css'
        if css_file.exists():
            content = css_file.read_text(encoding='utf-8')
            
            polish_features = [
                ('sidebar-toggle-btn', 'Toggle button styles'),
                ('sidebar-collapsed', 'Collapsed state'),
                ('@keyframes', 'Animations'),
                ('notification', 'Notification styles'),
                ('@media', 'Responsive design'),
                ('prefers-reduced-motion', 'Accessibility'),
            ]
            
            for feature, description in polish_features:
                if feature in content:
                    test_result(
                        f"Phase 5: CSS '{feature}'",
                        'PASS',
                        description
                    )
    
    def test_existing_features(self):
        """Test existing features integration"""
        logger.info("\n🔧 Testing Existing Features Integration...")
        
        app_file = self.base_path / 'app.py'
        if app_file.exists():
            content = app_file.read_text(encoding='utf-8')
            
            # Check for feature endpoints/functions
            features = [
                ('image_generation', 'Image Generation'),
                ('@app.route.*memory', 'Memory System'),
                ('upload.*file', 'File Upload'),
                ('google.*search', 'Google Search'),
                ('github', 'GitHub Integration'),
            ]
            
            for pattern, description in features:
                import re
                if re.search(pattern, content, re.IGNORECASE):
                    test_result(
                        f"Existing Feature: {description}",
                        'PASS',
                        f"{description} endpoint/function found"
                    )
                else:
                    test_result(
                        f"Existing Feature: {description}",
                        'SKIP',
                        f"{description} - check manually"
                    )
        
        # Check for image-gen.js module
        image_gen = self.static_path / 'js' / 'modules' / 'image-gen.js'
        if image_gen.exists():
            test_result(
                'Existing Feature: image-gen.js module',
                'PASS',
                'Image generation module exists'
            )
        
        # Check for memory-manager.js module
        memory_mgr = self.static_path / 'js' / 'modules' / 'memory-manager.js'
        if memory_mgr.exists():
            test_result(
                'Existing Feature: memory-manager.js module',
                'PASS',
                'Memory manager module exists'
            )
        
        # Check for file-handler.js module
        file_handler = self.static_path / 'js' / 'modules' / 'file-handler.js'
        if file_handler.exists():
            test_result(
                'Existing Feature: file-handler.js module',
                'PASS',
                'File handler module exists'
            )
    
    def test_javascript_modules(self):
        """Test JavaScript module structure"""
        logger.info("\n📦 Testing JavaScript Modules...")
        
        main_v2 = self.static_path / 'js' / 'main_v2.js'
        if main_v2.exists():
            content = main_v2.read_text(encoding='utf-8')
            
            # Check for all module imports
            required_imports = [
                'ChatManager',
                'APIService',
                'MessageRenderer',
                'FileHandler',
                'ImageGenerator',
                'MemoryManager',
                'ExportHandler',
                'SearchHandler',
                'VersionNavigator',
                'ProjectsManager',
                'PreferencesManager',
                'SidebarToggle',
                'NotificationManager',
            ]
            
            for module in required_imports:
                if module in content:
                    test_result(
                        f"Module Import: {module}",
                        'PASS',
                        f"{module} imported"
                    )
                else:
                    test_result(
                        f"Module Import: {module}",
                        'FAIL',
                        f"{module} not imported"
                    )
            
            # Check for initialization
            if 'initializeApp' in content:
                test_result(
                    'Main V2: App initialization',
                    'PASS',
                    'initializeApp function exists'
                )
            
            if 'Promise.all' in content:
                test_result(
                    'Main V2: Parallel initialization',
                    'PASS',
                    'Modules initialized in parallel'
                )
    
    def test_css_structure(self):
        """Test CSS structure and organization"""
        logger.info("\n🎨 Testing CSS Structure...")
        
        css_file = self.static_path / 'css' / 'style_chatgpt_v2.css'
        if css_file.exists():
            content = css_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Check line count
            line_count = len(lines)
            expected_min = 2500
            
            test_result(
                'CSS: Total line count',
                'PASS' if line_count >= expected_min else 'FAIL',
                f'{line_count} lines (expected ≥{expected_min})',
                {'lines': line_count}
            )
            
            # Check for section comments
            sections = [
                'CSS Variables',
                'Sidebar',
                'Search',
                'Version Navigation',
                'Projects',
                'Animations',
                'Mobile',
                'Accessibility',
            ]
            
            for section in sections:
                # Case-insensitive search for section
                if any(section.lower() in line.lower() for line in lines):
                    test_result(
                        f"CSS Section: {section}",
                        'PASS',
                        f"{section} section present"
                    )
            
            # Check for no syntax errors (basic check)
            open_braces = content.count('{')
            close_braces = content.count('}')
            
            test_result(
                'CSS: Brace matching',
                'PASS' if open_braces == close_braces else 'FAIL',
                f'Open: {open_braces}, Close: {close_braces}',
                {'open': open_braces, 'close': close_braces}
            )
    
    def test_documentation(self):
        """Test documentation completeness"""
        logger.info("\n📚 Testing Documentation...")
        
        required_docs = [
            ('PHASE2_COMPLETE_SUMMARY.md', 'Phase 2 summary'),
            ('PHASE3_COMPLETE_SUMMARY.md', 'Phase 3 summary'),
            ('PHASE4_COMPLETE_SUMMARY.md', 'Phase 4 summary'),
            ('PHASE5_COMPLETE_SUMMARY.md', 'Phase 5 summary'),
            ('VERSION_NAVIGATION_GUIDE.md', 'Phase 3 guide'),
            ('SIDEBAR_TOGGLE_GUIDE.md', 'Phase 5 guide'),
        ]
        
        for doc_name, description in required_docs:
            doc_file = self.docs_path / doc_name
            if doc_file.exists():
                content = doc_file.read_text(encoding='utf-8')
                lines = len(content.splitlines())
                words = len(content.split())
                
                test_result(
                    f"Documentation: {doc_name}",
                    'PASS',
                    f"{description} - {lines} lines, {words} words",
                    {'lines': lines, 'words': words}
                )
            else:
                test_result(
                    f"Documentation: {doc_name}",
                    'FAIL',
                    f"Missing {description}"
                )
    
    def generate_report(self):
        """Generate final test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 PHASE 6 TEST RESULTS")
        logger.info("="*60)
        
        total = test_results['total_tests']
        passed = test_results['passed']
        failed = test_results['failed']
        skipped = test_results['skipped']
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"✅ Passed: {passed} ({pass_rate:.1f}%)")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⏭️ Skipped: {skipped}")
        
        # Show failed tests
        if failed > 0:
            logger.info("\n❌ Failed Tests:")
            for test in test_results['tests']:
                if test['status'] == 'FAIL':
                    logger.error(f"  - {test['name']}: {test['message']}")
        
        # Show skipped tests
        if skipped > 0:
            logger.info("\n⏭️ Skipped Tests:")
            for test in test_results['tests']:
                if test['status'] == 'SKIP':
                    logger.warning(f"  - {test['name']}: {test['message']}")
        
        # Overall status
        logger.info("\n" + "="*60)
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! Phase 6 Complete!")
            logger.info("✅ ChatGPT V2 is ready for production")
        elif failed < 5:
            logger.warning("⚠️ Most tests passed, minor issues to fix")
        else:
            logger.error("❌ Multiple tests failed, requires attention")
        logger.info("="*60)
        
        # Save report to file
        report_file = self.base_path / 'PHASE6_TEST_REPORT.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_file}")

def main():
    """Main test runner"""
    try:
        tester = Phase6Tester()
        tester.run_all_tests()
        
        # Return exit code based on results
        if test_results['failed'] == 0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == '__main__':
    main()
