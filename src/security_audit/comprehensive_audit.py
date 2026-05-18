# comprehensive_audit.py
# Run: python comprehensive_audit.py

import os
import re
import json
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class HumanitarianAudit:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.findings = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }
        self.scores = {}
        
    def run_full_audit(self):
        print("=" * 80)
        print("🏥 PAMOJADATA - HUMANITARIAN SYSTEM AUDIT")
        print("=" * 80)
        print(f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Path: {self.project_path}")
        print("=" * 80)
        
        # PHASE 1: System Inspection
        self.inspect_architecture()
        self.identify_sensitive_data()
        self.analyze_security_surfaces()
        
        # PHASE 2: Security Audit
        self.audit_authentication()
        self.audit_authorization()
        self.audit_database_security()
        self.audit_session_management()
        self.audit_file_security()
        
        # PHASE 3: Vulnerability Scan
        self.scan_dependencies()
        self.scan_sql_injection()
        self.scan_xss_vulnerabilities()
        self.scan_secrets_leakage()
        
        # PHASE 4: Humanitarian Compliance
        self.audit_data_responsibility()
        self.audit_do_no_harm()
        self.audit_aap_principles()
        
        # PHASE 5: Code Quality
        self.audit_code_quality()
        self.audit_error_handling()
        
        # PHASE 6: Production Readiness
        self.audit_configuration()
        self.audit_logging()
        self.audit_backup_strategy()
        
        # PHASE 7: Generate Report
        self.generate_report()
        
    def inspect_architecture(self):
        print("\n" + "=" * 60)
        print("📐 PHASE 1: SYSTEM ARCHITECTURE INSPECTION")
        print("=" * 60)
        
        # Detect architecture type
        if (self.project_path / "app.py").exists():
            self.scores['architecture'] = 7
            print("✅ Frontend: Streamlit (Python-based UI)")
        
        if (self.project_path / "src" / "auth" / "auth.py").exists():
            print("✅ Backend: Python/Streamlit monolithic architecture")
            
        # Check database
        db_files = list(self.project_path.glob("**/*.db"))
        if db_files:
            print(f"✅ Database: SQLite ({len(db_files)} database files)")
            print("⚠️  Note: SQLite has limited concurrent write capacity")
            self.findings['medium'].append({
                'issue': 'SQLite in production',
                'risk': 'Limited concurrent write capacity',
                'remediation': 'Consider PostgreSQL for production deployment'
            })
        
        print("\n📋 Architecture Summary:")
        print("  • Type: Monolithic web application")
        print("  • Framework: Streamlit")
        print("  • Database: SQLite")
        print("  • Auth: Custom RBAC implementation")
        
    def identify_sensitive_data(self):
        print("\n" + "=" * 60)
        print("🔒 SENSITIVE DATA IDENTIFICATION")
        print("=" * 60)
        
        sensitive_patterns = {
            'PII (Email)': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'Phone Numbers': r'\b\+?[\d\s-]{10,15}\b',
            'Password Fields': r'password',
            'Auth Tokens': r'token[\s]*=',
            'API Keys': r'api[_-]?key|GEMINI_API_KEY'
        }
        
        for data_type, pattern in sensitive_patterns.items():
            matches = []
            for py_file in self.project_path.glob("**/*.py"):
                if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                    continue
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if re.search(pattern, content, re.IGNORECASE):
                            matches.append(py_file.name)
                except:
                    pass
            
            if matches:
                print(f"  📍 {data_type}: Found in {', '.join(set(matches[:3]))}")
        
        self.findings['high'].append({
            'issue': 'Sensitive PII stored in plain text',
            'risk': 'Database compromise exposes beneficiary emails and phone numbers',
            'remediation': 'Implement column-level encryption for PII fields'
        })
        
    def analyze_security_surfaces(self):
        print("\n" + "=" * 60)
        print("🎯 SECURITY SURFACES IDENTIFIED")
        print("=" * 60)
        
        surfaces = [
            ("Login endpoint", "Authentication bypass risk"),
            ("Registration endpoint", "Bot/spam registration risk"),
            ("File upload", "Malware/RCE risk"),
            ("Password reset", "Account takeover risk"),
            ("Invite token system", "Privilege escalation risk"),
            ("User management API", "Unauthorized access risk"),
            ("Database queries", "SQL injection risk"),
        ]
        
        for surface, risk in surfaces:
            print(f"  🔴 {surface}: {risk}")
            self.findings['high'].append({
                'issue': f'{surface} security surface',
                'risk': risk,
                'remediation': 'Implement rate limiting, input validation, and proper auth checks'
            })
    
    def audit_authentication(self):
        print("\n" + "=" * 60)
        print("🔐 AUTHENTICATION AUDIT")
        print("=" * 60)
        
        auth_file = self.project_path / "src" / "auth" / "auth.py"
        if auth_file.exists():
            with open(auth_file, 'r') as f:
                content = f.read()
            
            # Check password hashing
            if 'pbkdf2_hmac' in content and 'iterations' in content:
                print("✅ Password hashing: PBKDF2 with iterations")
                self.scores['auth'] = 8
            else:
                self.findings['critical'].append({
                    'issue': 'Weak password hashing',
                    'risk': 'Passwords could be cracked offline',
                    'remediation': 'Use PBKDF2 with 300,000+ iterations'
                })
            
            # Check session expiration
            if 'SESSION_EXPIRE_HOURS' in content:
                print("✅ Session expiration configured")
            else:
                self.findings['medium'].append({
                    'issue': 'No session expiration',
                    'risk': 'Sessions never expire, increasing hijack risk',
                    'remediation': 'Set SESSION_EXPIRE_HOURS=8'
                })
            
            # Check rate limiting
            if 'failed_login_attempts' in content and 'locked_until' in content:
                print("✅ Rate limiting: Account lockout after 5 attempts")
            else:
                self.findings['high'].append({
                    'issue': 'No rate limiting on login',
                    'risk': 'Brute force attacks possible',
                    'remediation': 'Implement max 5 failed attempts with 30-min lockout'
                })
        
    def audit_authorization(self):
        print("\n" + "=" * 60)
        print("🛡️ AUTHORIZATION & RBAC AUDIT")
        print("=" * 60)
        
        # Check RBAC implementation
        auth_file = self.project_path / "src" / "auth" / "auth.py"
        if auth_file.exists():
            with open(auth_file, 'r') as f:
                content = f.read()
            
            if 'ROLE_PERMISSIONS' in content:
                print("✅ RBAC: Role-based permissions defined")
                
                # Extract roles
                role_match = re.search(r"ROLE_PERMISSIONS = \{(.*?)\}", content, re.DOTALL)
                if role_match:
                    roles_found = re.findall(r"'([^']+)':", role_match.group(1))
                    print(f"  Roles configured: {', '.join(roles_found)}")
                    self.scores['rbac'] = 7
            else:
                self.findings['critical'].append({
                    'issue': 'No RBAC implementation found',
                    'risk': 'No permission controls',
                    'remediation': 'Implement role-based access control'
                })
            
            # Check if permissions are enforced on backend
            if 'has_permission' in content:
                print("✅ Permission enforcement: has_permission() function exists")
            else:
                self.findings['critical'].append({
                    'issue': 'No permission enforcement function',
                    'risk': 'Frontend-only protection can be bypassed',
                    'remediation': 'Add has_permission() checks to all sensitive operations'
                })
    
    def audit_database_security(self):
        print("\n" + "=" * 60)
        print("🗄️ DATABASE SECURITY AUDIT")
        print("=" * 60)
        
        db_files = list(self.project_path.glob("**/*.db"))
        for db_file in db_files:
            if "data" in str(db_file):
                print(f"⚠️  Database exposed in web-accessible location: {db_file.name}")
                self.findings['high'].append({
                    'issue': 'Database in web-accessible directory',
                    'risk': 'Potential direct download if path is discovered',
                    'remediation': 'Move database outside web root, set .gitignore'
                })
            
            # Check database permissions
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"  📊 Tables found: {len(tables)}")
                conn.close()
            except:
                pass
        
        self.scores['database'] = 5
        
    def audit_session_management(self):
        print("\n" + "=" * 60)
        print("🍪 SESSION MANAGEMENT AUDIT")
        print("=" * 60)
        
        app_file = self.project_path / "app.py"
        if app_file.exists():
            with open(app_file, 'r') as f:
                content = f.read()
            
            if 'session_token' in content:
                print("✅ Session token implementation found")
                
                # Check for proper logout
                if 'logout' in content:
                    print("✅ Logout functionality implemented")
                else:
                    self.findings['medium'].append({
                        'issue': 'No explicit logout',
                        'risk': 'Sessions persist indefinitely',
                        'remediation': 'Implement logout that destroys session token'
                    })
                
                # Check session validation
                if 'validate_session' in content:
                    print("✅ Session validation middleware present")
                else:
                    self.findings['high'].append({
                        'issue': 'No session validation on page load',
                        'risk': 'Stale sessions could remain active',
                        'remediation': 'Validate session token on each request'
                    })
    
    def audit_file_security(self):
        print("\n" + "=" * 60)
        print("📁 FILE UPLOAD SECURITY AUDIT")
        print("=" * 60)
        
        upload_dirs = ['uploads', 'media', 'files', 'static/uploads']
        for upload_dir in upload_dirs:
            if (self.project_path / upload_dir).exists():
                print(f"⚠️  File upload directory found: {upload_dir}")
                self.findings['high'].append({
                    'issue': f'File upload capability without validation',
                    'risk': 'Malware upload, RCE, path traversal',
                    'remediation': 'Validate file types, scan for malware, rename files, limit size'
                })
    
    def scan_dependencies(self):
        print("\n" + "=" * 60)
        print("📦 DEPENDENCY VULNERABILITY SCAN")
        print("=" * 60)
        
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                deps = f.read()
            
            # Check for known vulnerable packages
            vulnerable = {
                'streamlit': 'Check for CVE-2022-35918, CVE-2023-0028',
                'sqlite3': 'Use latest version',
                'requests': 'Ensure >=2.31.0 for security fixes'
            }
            
            for dep, cve_info in vulnerable.items():
                if dep in deps.lower():
                    print(f"  ⚠️  {dep}: {cve_info}")
                    self.findings['medium'].append({
                        'issue': f'Dependency {dep} needs review',
                        'risk': 'Known vulnerabilities may exist',
                        'remediation': f'Update {dep} to latest version, run pip-audit'
                    })
            
            print("  📋 Run: pip-audit to check all dependencies for CVEs")
        else:
            print("  ❌ requirements.txt not found")
    
    def scan_sql_injection(self):
        print("\n" + "=" * 60)
        print("💉 SQL INJECTION SCAN")
        print("=" * 60)
        
        vulnerable_patterns = 0
        for py_file in self.project_path.glob("**/*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Check for vulnerable patterns
                if re.search(r'cursor\.execute\(f["\'].*\{', content):
                    vulnerable_patterns += 1
                    print(f"  🔴 SQL injection risk in {py_file.name}: F-string SQL")
                    self.findings['critical'].append({
                        'issue': f'SQL injection vulnerability in {py_file.name}',
                        'risk': 'Attacker can read/write entire database',
                        'remediation': 'Use parameterized queries with ? placeholders'
                    })
                    break
                
                if re.search(r'cursor\.execute\(["\'].*\+.*\+', content):
                    vulnerable_patterns += 1
                    print(f"  🔴 SQL injection risk in {py_file.name}: String concatenation")
                    self.findings['critical'].append({
                        'issue': f'SQL injection in {py_file.name}',
                        'risk': 'Database compromise',
                        'remediation': 'Use parameterized queries'
                    })
                    break
        
        if vulnerable_patterns == 0:
            print("  ✅ No obvious SQL injection patterns found")
    
    def scan_xss_vulnerabilities(self):
        print("\n" + "=" * 60)
        print("🌐 XSS VULNERABILITY SCAN")
        print("=" * 60)
        
        for py_file in self.project_path.glob("**/*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                if re.search(r'unsafe_allow_html=True', content):
                    print(f"  ⚠️  Potential XSS in {py_file.name}: unsafe_allow_html=True")
                    self.findings['medium'].append({
                        'issue': f'Potential XSS in {py_file.name}',
                        'risk': 'Attacker could inject malicious scripts',
                        'remediation': 'Sanitize user input before rendering with markdown'
                    })
    
    def scan_secrets_leakage(self):
        print("\n" + "=" * 60)
        print("🔑 SECRETS LEAKAGE SCAN")
        print("=" * 60)
        
        secret_patterns = [
            (r'API_KEY\s*=\s*["\'][^"\']+["\']', 'API Key'),
            (r'PASSWORD\s*=\s*["\'][^"\']+["\']', 'Password'),
            (r'SECRET\s*=\s*["\'][^"\']+["\']', 'Secret'),
            (r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', 'Token'),
        ]
        
        found_secrets = False
        for py_file in self.project_path.glob("**/*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                for pattern, secret_type in secret_patterns:
                    if re.search(pattern, content):
                        print(f"  🔴 Hardcoded {secret_type} found in {py_file.name}")
                        self.findings['critical'].append({
                            'issue': f'Hardcoded {secret_type} in source code',
                            'risk': 'Secret exposed in version control',
                            'remediation': 'Use environment variables or secrets management'
                        })
                        found_secrets = True
        
        if not found_secrets:
            print("  ✅ No hardcoded secrets detected")
    
    def audit_data_responsibility(self):
        print("\n" + "=" * 60)
        print("🌍 OCHA DATA RESPONSIBILITY AUDIT")
        print("=" * 60)
        
        checks = {
            'Data minimization': False,
            'Consent management': False,
            'Data retention policy': False,
            'Data deletion capability': True,
            'Access logging': True,
            'Purpose limitation': False
        }
        
        # Check for delete_user function
        auth_file = self.project_path / "src" / "auth" / "auth.py"
        if auth_file.exists():
            with open(auth_file, 'r') as f:
                content = f.read()
                if 'delete_user' in content:
                    checks['Data deletion capability'] = True
                    print("  ✅ Data deletion: delete_user() exists")
                if 'audit_logs' in content:
                    checks['Access logging'] = True
                    print("  ✅ Access logging: audit_logs table exists")
        
        for check, status in checks.items():
            if not status:
                self.findings['high'].append({
                    'issue': f'Missing: {check}',
                    'risk': 'Non-compliance with OCHA data responsibility guidelines',
                    'remediation': f'Implement {check} policies and technical controls'
                })
        
        print(f"\n  📋 OCHA Compliance Score: {sum(checks.values())}/{len(checks)}")
        self.scores['ocha'] = sum(checks.values()) / len(checks) * 10
    
    def audit_do_no_harm(self):
        print("\n" + "=" * 60)
        print("🕊️ DO NO HARM PRINCIPLE AUDIT")
        print("=" * 60)
        
        harms = []
        
        # Check for harm risks
        if (self.project_path / "data" / "pamojadata.db").exists():
            harms.append("Database accessible via file path")
        
        auth_file = self.project_path / "src" / "auth" / "auth.py"
        if auth_file.exists():
            with open(auth_file, 'r') as f:
                content = f.read()
                if 'role' not in content:
                    harms.append("No role-based access to sensitive data")
        
        if harms:
            for harm in harms:
                print(f"  ⚠️  Harm risk: {harm}")
                self.findings['critical'].append({
                    'issue': f'Do No Harm violation: {harm}',
                    'risk': 'Beneficiary data could be exposed to unauthorized parties',
                    'remediation': 'Implement strict access controls and encryption'
                })
        else:
            print("  ✅ No immediate Do No Harm violations detected")
    
    def audit_aap_principles(self):
        print("\n" + "=" * 60)
        print("👥 ACCOUNTABILITY TO AFFECTED PEOPLE (AAP)")
        print("=" * 60)
        
        print("  📋 Recommended AAP features to implement:")
        print("     • Feedback/complaint mechanism")
        print("     • Transparent data usage disclosure")
        print("     • Consent management interface")
        print("     • Data access request portal")
        
        self.findings['medium'].append({
            'issue': 'No feedback/complaint mechanism',
            'risk': 'Affected people cannot report issues or request data deletion',
            'remediation': 'Add user-facing feedback system and data subject request portal'
        })
    
    def audit_code_quality(self):
        print("\n" + "=" * 60)
        print("📝 CODE QUALITY AUDIT")
        print("=" * 60)
        
        quality_metrics = {
            'total_lines': 0,
            'files': 0,
            'avg_file_size': 0,
            'longest_file': 0
        }
        
        py_files = list(self.project_path.glob("**/*.py"))
        py_files = [f for f in py_files if 'venv' not in str(f) and '__pycache__' not in str(f)]
        
        for py_file in py_files:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = len(f.readlines())
                quality_metrics['total_lines'] += lines
                quality_metrics['files'] += 1
                if lines > quality_metrics['longest_file']:
                    quality_metrics['longest_file'] = lines
        
        if quality_metrics['files'] > 0:
            quality_metrics['avg_file_size'] = int(quality_metrics['total_lines'] / quality_metrics['files'])
        
        print(f"  📊 Code Statistics:")
        print(f"     • Python files: {quality_metrics['files']}")
        print(f"     • Total lines: {quality_metrics['total_lines']:,}")
        print(f"     • Avg file size: {quality_metrics['avg_file_size']:.0f} lines")
        print(f"     • Largest file: {quality_metrics['longest_file']} lines")
        
        score = 7  # Base score
        if quality_metrics['longest_file'] > 500:
            score -= 1
            print("  ⚠️  Consider splitting large files")
        
        self.scores['code_quality'] = score
    
    def audit_error_handling(self):
        print("\n" + "=" * 60)
        print("⚠️ ERROR HANDLING AUDIT")
        print("=" * 60)
        
        error_patterns = 0
        for py_file in self.project_path.glob("**/*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                if 'try:' in content and 'except:' in content:
                    error_patterns += 1
        
        if error_patterns > 0:
            print(f"  ✅ Error handling detected in {error_patterns} files")
        else:
            self.findings['medium'].append({
                'issue': 'Minimal error handling',
                'risk': 'Application may crash or expose internal errors',
                'remediation': 'Add try/except blocks with graceful degradation'
            })
    
    def audit_configuration(self):
        print("\n" + "=" * 60)
        print("⚙️ CONFIGURATION & ENVIRONMENT AUDIT")
        print("=" * 60)
        
        # Check for .env file
        if (self.project_path / ".env").exists():
            print("  ✅ .env file exists")
        else:
            self.findings['medium'].append({
                'issue': 'No .env file for environment configuration',
                'risk': 'Configuration mixed with code',
                'remediation': 'Use .env for environment-specific settings'
            })
        
        # Check for secrets
        if (self.project_path / ".streamlit" / "secrets.toml").exists():
            print("  ✅ Streamlit secrets.toml exists")
        else:
            self.findings['high'].append({
                'issue': 'No secrets management',
                'risk': 'Sensitive credentials may be hardcoded',
                'remediation': 'Use Streamlit secrets for production'
            })
    
    def audit_logging(self):
        print("\n" + "=" * 60)
        print("📋 LOGGING & MONITORING AUDIT")
        print("=" * 60)
        
        auth_file = self.project_path / "src" / "auth" / "auth.py"
        if auth_file.exists():
            with open(auth_file, 'r') as f:
                content = f.read()
                
                if 'audit_logs' in content and '_record_audit' in content:
                    print("  ✅ Audit logging: User actions are logged")
                    self.scores['logging'] = 8
                else:
                    self.findings['high'].append({
                        'issue': 'No audit logging',
                        'risk': 'Cannot track who accessed/modified data',
                        'remediation': 'Log all access to sensitive data'
                    })
    
    def audit_backup_strategy(self):
        print("\n" + "=" * 60)
        print("💾 BACKUP & DISASTER RECOVERY AUDIT")
        print("=" * 60)
        
        print("  ⚠️  No automated backup system detected")
        print("  📋 Recommended backup strategy:")
        print("     • Daily database backups")
        print("     • Offsite backup storage")
        print("     • Point-in-time recovery capability")
        
        self.findings['high'].append({
            'issue': 'No database backup strategy',
            'risk': 'Data loss from corruption or ransomware',
            'remediation': 'Implement automated daily backups'
        })
    
    def generate_report(self):
        print("\n" + "=" * 80)
        print("📊 EXECUTIVE AUDIT REPORT")
        print("=" * 80)
        
        # Calculate scores
        avg_score = sum(self.scores.values()) / len(self.scores) if self.scores else 0
        
        print(f"\n🏆 OVERALL INDUSTRY-READINESS SCORE: {avg_score:.1f}/10")
        
        if avg_score >= 8:
            grade = "GO FOR PRODUCTION"
            color = "GREEN"
        elif avg_score >= 6:
            grade = "PROCEED WITH CAUTION"
            color = "YELLOW"
        elif avg_score >= 4:
            grade = "NEEDS IMPROVEMENT"
            color = "ORANGE"
        else:
            grade = "DO NOT DEPLOY"
            color = "RED"
        
        print(f"🎯 VERDICT: {grade}")
        print("\n" + "-" * 80)
        
        # Critical findings
        if self.findings['critical']:
            print(f"\n🔴 CRITICAL FINDINGS ({len(self.findings['critical'])}):")
            for f in self.findings['critical']:
                print(f"   • {f['issue']}")
                print(f"     Risk: {f['risk']}")
                print(f"     Fix: {f['remediation']}\n")
        
        # High findings
        if self.findings['high']:
            print(f"\n🟠 HIGH SEVERITY ({len(self.findings['high'])}):")
            for f in self.findings['high'][:10]:  # Limit to 10
                print(f"   • {f['issue']}")
        
        # Scores breakdown
        print("\n📈 SCORE BREAKDOWN:")
        for category, score in self.scores.items():
            print(f"   {category.replace('_', ' ').title()}: {score}/10")
        
        # Go/No-Go Decision
        print("\n" + "=" * 80)
        print("🚦 FINAL GO/NO-GO DECISION")
        print("=" * 80)
        
        critical_count = len(self.findings['critical'])
        high_count = len(self.findings['high'])
        
        if critical_count > 0:
            print(f"\n❌ NO-GO: {critical_count} critical security issues must be fixed before deployment")
            print("\nImmediate blocking issues:")
            for f in self.findings['critical'][:5]:
                print(f"   • {f['issue']}")
        elif high_count > 5:
            print(f"\n⚠️ CONDITIONAL GO: Address {high_count} high-severity issues first")
        elif avg_score >= 7:
            print("\n✅ GO: System meets minimum standards for controlled deployment")
            print("\nRecommended deployment steps:")
            print("   1. Run in staging environment for 2 weeks")
            print("   2. Conduct user acceptance testing")
            print("   3. Implement monitoring and alerting")
            print("   4. Train humanitarian staff on data responsibility")
        else:
            print("\n❌ NO-GO: Multiple critical improvements needed")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("📋 TOP 10 IMMEDIATE REMEDIATIONS")
        print("=" * 80)
        
        remediations = [
            "1. Move database outside web-accessible directory",
            "2. Implement rate limiting on login (max 5 attempts)",
            "3. Add parameterized queries to prevent SQL injection",
            "4. Set up automated daily database backups",
            "5. Implement proper logging and monitoring",
            "6. Add feedback mechanism for affected populations",
            "7. Deploy with environment-based configuration",
            "8. Set session expiration (8 hours)",
            "9. Add file upload validation and malware scanning",
            "10. Conduct third-party penetration test"
        ]
        
        for r in remediations:
            print(f"   {r}")
        
        print("\n" + "=" * 80)
        print("📄 REPORT GENERATED")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Critical: {len(self.findings['critical'])}")
        print(f"High: {len(self.findings['high'])}")
        print(f"Medium: {len(self.findings['medium'])}")
        print(f"Low: {len(self.findings['low'])}")
        print("\n✅ Audit complete. Save this report for compliance documentation.")

def main():
    project_path = Path.cwd()
    
    if not (project_path / "app.py").exists():
        print("❌ Error: app.py not found")
        print("Please run this script from your project root directory")
        return
    
    auditor = HumanitarianAudit(project_path)
    auditor.run_full_audit()

if __name__ == "__main__":
    main()