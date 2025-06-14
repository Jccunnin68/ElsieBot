#!/usr/bin/env python3
"""
Phase 1: Codebase State Documentation
=====================================

This script documents the current state of the codebase before beginning
the deprecated function removal process. This serves as a safety backup
and reference for the refactor.

This is part of the Roleplay Deprecation Refactor Plan Phase 1.
"""

import sys
import os
import importlib
import ast
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def document_current_codebase_state():
    """
    Document the current state of all roleplay-related modules.
    This creates a comprehensive inventory before the refactor.
    """
    print("=" * 80)
    print("📋 PHASE 1: CODEBASE STATE DOCUMENTATION")
    print("=" * 80)
    print()
    
    # Document all roleplay-related modules
    modules_to_document = [
        # Core routing
        'handlers.ai_logic.response_router',
        'handlers.ai_logic.strategy_engine',
        'handlers.ai_logic.roleplay_handler',
        
        # Decision engines
        'handlers.ai_logic.response_decision_engine',
        'handlers.ai_logic.response_decision',
        
        # Attention modules
        'handlers.ai_attention.state_manager',
        'handlers.ai_attention.context_gatherer',
        'handlers.ai_attention.conversation_memory',
        'handlers.ai_attention.response_logic',
        
        # Emotional intelligence
        'handlers.ai_emotion.priority_resolution',
        'handlers.ai_emotion.emotional_analysis',
        'handlers.ai_emotion.conversation_emotions',
        
        # Coordinators
        'handlers.ai_coordinator.response_coordinator',
        'handlers.ai_coordinator.ai_engine',
    ]
    
    codebase_state = {
        'modules': {},
        'deprecated_functions': [],
        'enhanced_functions': [],
        'critical_imports': [],
        'total_functions': 0,
        'total_classes': 0
    }
    
    print("📂 ANALYZING MODULES:")
    for module_name in modules_to_document:
        print(f"\n   📄 {module_name}")
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Get the source file
            source_file = module.__file__
            if source_file.endswith('.pyc'):
                source_file = source_file[:-1]  # Remove 'c' from .pyc
            
            # Parse the source code
            with open(source_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            
            # Analyze the module
            module_analysis = analyze_module(tree, source_code, module_name)
            codebase_state['modules'][module_name] = module_analysis
            
            # Update totals
            codebase_state['total_functions'] += len(module_analysis['functions'])
            codebase_state['total_classes'] += len(module_analysis['classes'])
            
            # Identify deprecated functions
            for func in module_analysis['functions']:
                if is_deprecated_function(func, module_name):
                    codebase_state['deprecated_functions'].append({
                        'module': module_name,
                        'function': func['name'],
                        'reason': get_deprecation_reason(func['name'], module_name)
                    })
                elif is_enhanced_function(func, module_name):
                    codebase_state['enhanced_functions'].append({
                        'module': module_name,
                        'function': func['name']
                    })
            
            print(f"      ✅ Functions: {len(module_analysis['functions'])}")
            print(f"      ✅ Classes: {len(module_analysis['classes'])}")
            print(f"      ✅ Imports: {len(module_analysis['imports'])}")
            
        except Exception as e:
            print(f"      ❌ Error analyzing {module_name}: {e}")
            codebase_state['modules'][module_name] = {'error': str(e)}
    
    # Document critical imports
    codebase_state['critical_imports'] = document_critical_imports()
    
    # Generate summary
    print(f"\n{'=' * 60}")
    print("📊 CODEBASE STATE SUMMARY")
    print(f"{'=' * 60}")
    print(f"📦 Modules analyzed: {len(codebase_state['modules'])}")
    print(f"🔧 Total functions: {codebase_state['total_functions']}")
    print(f"🏗️  Total classes: {codebase_state['total_classes']}")
    print(f"⚠️  Deprecated functions: {len(codebase_state['deprecated_functions'])}")
    print(f"✨ Enhanced functions: {len(codebase_state['enhanced_functions'])}")
    print(f"📥 Critical imports: {len(codebase_state['critical_imports'])}")
    
    # List deprecated functions
    print(f"\n📋 DEPRECATED FUNCTIONS TO REMOVE:")
    for func in codebase_state['deprecated_functions']:
        print(f"   ❌ {func['module']}.{func['function']} - {func['reason']}")
    
    # List enhanced functions
    print(f"\n📋 ENHANCED FUNCTIONS (KEEP):")
    for func in codebase_state['enhanced_functions']:
        print(f"   ✅ {func['module']}.{func['function']}")
    
    # Critical imports
    print(f"\n📋 CRITICAL IMPORTS:")
    for imp in codebase_state['critical_imports']:
        print(f"   📥 {imp}")
    
    return codebase_state


def analyze_module(tree, source_code, module_name):
    """Analyze a module's AST to extract functions, classes, and imports."""
    analysis = {
        'functions': [],
        'classes': [],
        'imports': [],
        'source_lines': len(source_code.split('\n'))
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            analysis['functions'].append({
                'name': node.name,
                'line': node.lineno,
                'args': [arg.arg for arg in node.args.args],
                'docstring': ast.get_docstring(node) or '',
                'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
            })
        elif isinstance(node, ast.ClassDef):
            analysis['classes'].append({
                'name': node.name,
                'line': node.lineno,
                'bases': [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                'docstring': ast.get_docstring(node) or ''
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                analysis['imports'].append({
                    'type': 'import',
                    'module': alias.name,
                    'alias': alias.asname
                })
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                analysis['imports'].append({
                    'type': 'from_import',
                    'module': node.module,
                    'name': alias.name,
                    'alias': alias.asname
                })
    
    return analysis


def is_deprecated_function(func, module_name):
    """Check if a function is deprecated based on our refactor plan."""
    deprecated_functions = {
        # From ai_logic.strategy_engine
        'handlers.ai_logic.strategy_engine': [
            'determine_response_strategy'  # Replaced by enhanced decision engine
        ],
        
        # From ai_logic.roleplay_handler  
        'handlers.ai_logic.roleplay_handler': [
            'handle_roleplay_message',  # Replaced by enhanced intelligence
            'build_roleplay_strategy',  # Replaced by enhanced decision engine
            'detect_roleplay_response_type'  # Replaced by contextual analysis
        ],
        
        # From ai_attention.response_logic
        'handlers.ai_attention.response_logic': [
            'should_elsie_respond_in_roleplay'  # Replaced by enhanced decision engine
        ],
        
        # From ai_attention.conversation_memory
        'handlers.ai_attention.conversation_memory': [
            'getNextResponseEnhanced'  # Moved to response_decision_engine
        ],
        
        # From ai_coordinator.response_coordinator
        'handlers.ai_coordinator.response_coordinator': [
            'coordinate_response'  # Replaced by enhanced routing
        ]
    }
    
    module_deprecated = deprecated_functions.get(module_name, [])
    return func['name'] in module_deprecated


def is_enhanced_function(func, module_name):
    """Check if a function is part of the enhanced system."""
    enhanced_functions = {
        'handlers.ai_logic.response_router': [
            '_handle_roleplay_with_enhanced_intelligence',
            'route_message_to_handler'
        ],
        'handlers.ai_logic.response_decision_engine': [
            'getNextResponseEnhanced',
            'create_response_decision_engine'
        ],
        'handlers.ai_attention.context_gatherer': [
            'build_contextual_cues'
        ],
        'handlers.ai_emotion.priority_resolution': [
            'resolve_priority_conflict',
            'resolve_emotional_vs_group_conflict'
        ]
    }
    
    module_enhanced = enhanced_functions.get(module_name, [])
    return func['name'] in module_enhanced


def get_deprecation_reason(func_name, module_name):
    """Get the reason why a function is deprecated."""
    reasons = {
        'determine_response_strategy': 'Replaced by enhanced decision engine with emotional intelligence',
        'handle_roleplay_message': 'Replaced by enhanced intelligence system',
        'build_roleplay_strategy': 'Replaced by enhanced decision engine',
        'detect_roleplay_response_type': 'Replaced by contextual analysis',
        'should_elsie_respond_in_roleplay': 'Replaced by enhanced decision engine',
        'getNextResponseEnhanced': 'Moved to response_decision_engine',
        'coordinate_response': 'Replaced by enhanced routing'
    }
    
    return reasons.get(func_name, 'Part of deprecated legacy system')


def document_critical_imports():
    """Document critical imports that need to be preserved."""
    critical_imports = [
        'handlers.ai_logic.response_router.route_message_to_handler',
        'handlers.ai_logic.response_decision_engine.create_response_decision_engine',
        'handlers.ai_attention.context_gatherer.build_contextual_cues',
        'handlers.ai_attention.state_manager.get_roleplay_state',
        'handlers.ai_emotion.priority_resolution.resolve_priority_conflict',
        'handlers.ai_attention.contextual_cues.ResponseDecision',
        'handlers.ai_attention.contextual_cues.ResponseType',
        'handlers.ai_attention.contextual_cues.ElsieContextualCues'
    ]
    
    return critical_imports


def create_rollback_plan():
    """Create a rollback plan in case we need to revert changes."""
    rollback_plan = {
        'git_commands': [
            'git add .',
            'git commit -m "Phase 1: Pre-refactor state backup"',
            'git tag phase1-backup',
            'git push origin phase1-backup'
        ],
        'recovery_steps': [
            '1. If refactor fails, checkout the backup tag',
            '2. git checkout phase1-backup',
            '3. Restore from backup state',
            '4. Re-run validation tests'
        ],
        'validation_command': 'python ai_agent/tests/phase1_enhanced_pathway_validation.py'
    }
    
    print(f"\n📋 ROLLBACK PLAN:")
    print(f"{'=' * 40}")
    print(f"🔄 Git backup commands:")
    for cmd in rollback_plan['git_commands']:
        print(f"   {cmd}")
    
    print(f"\n🚨 Recovery steps:")
    for step in rollback_plan['recovery_steps']:
        print(f"   {step}")
    
    print(f"\n✅ Validation command:")
    print(f"   {rollback_plan['validation_command']}")
    
    return rollback_plan


if __name__ == "__main__":
    try:
        # Document codebase state
        codebase_state = document_current_codebase_state()
        
        # Create rollback plan
        rollback_plan = create_rollback_plan()
        
        # Final status
        print(f"\n{'=' * 80}")
        print("🏁 PHASE 1 DOCUMENTATION COMPLETE")
        print("=" * 80)
        print("✅ Codebase state documented")
        print("✅ Deprecated functions identified")
        print("✅ Enhanced functions catalogued")
        print("✅ Rollback plan created")
        print("🚀 Ready for Phase 1 validation testing")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in Phase 1 documentation: {e}")
        import traceback
        traceback.print_exc() 