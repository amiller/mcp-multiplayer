#!/usr/bin/env python3
"""
Test fixtures for bot sandboxing - these bots intentionally use restricted operations
and should be blocked by RestrictedPython.

Used to verify the sandbox is working correctly.
"""

# SandboxProbeBot - Attempts to access os/subprocess/filesystem
import os, sys, subprocess, platform, socket, glob

class SandboxProbeBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        self.params = params

    def on_init(self):
        self.ctx.post("bot", {
            "type": "ready",
            "message": "SandboxProbe ready! Commands: 'probe', 'env', 'files', 'net', 'proc', 'perms'"
        })

    def on_message(self, msg):
        if msg.get("kind") != "user":
            return
        text = msg.get("body", {}).get("text", "").lower().strip()

        if text == "probe":
            self.full_probe()
        elif text == "env":
            self.probe_env()
        elif text == "files":
            self.probe_files()
        elif text == "net":
            self.probe_network()
        elif text == "proc":
            self.probe_process()
        elif text == "perms":
            self.probe_permissions()

    def full_probe(self):
        info = []
        info.append(f"Python: {sys.version}")
        info.append(f"Platform: {platform.platform()}")
        info.append(f"CWD: {os.getcwd()}")
        info.append(f"User: {os.getuid()}/{os.geteuid()}")
        info.append(f"Modules: {len(sys.modules)} loaded")
        info.append(f"Path: {sys.path[:3]}")

        self.ctx.post("bot", {"type": "probe", "info": "\n".join(info)})

    def probe_env(self):
        env_vars = dict(os.environ)
        sensitive = {k: v for k, v in env_vars.items()
                    if any(s in k.lower() for s in ['token', 'key', 'secret', 'pass', 'auth', 'api'])}

        self.ctx.post("bot", {
            "type": "env",
            "total": len(env_vars),
            "sensitive": sensitive,
            "all": list(env_vars.keys())[:20]
        })

    def probe_files(self):
        paths = []
        for pattern in ['*.py', '*.json', '*.env', '/tmp/*', '/home/*/.ssh/*', '~/.aws/*']:
            try:
                paths.extend(glob.glob(pattern, recursive=True)[:5])
            except:
                pass

        self.ctx.post("bot", {
            "type": "files",
            "accessible": paths,
            "can_read_root": os.access('/', os.R_OK),
            "can_write_tmp": os.access('/tmp', os.W_OK)
        })

    def probe_network(self):
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except:
            ip = "unknown"

        # Try to make external connection
        can_connect = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
            can_connect = True
            s.close()
        except:
            pass

        self.ctx.post("bot", {
            "type": "network",
            "hostname": hostname,
            "ip": ip,
            "external_access": can_connect
        })

    def probe_process(self):
        info = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "executable": sys.executable,
            "argv": sys.argv,
        }

        # Try subprocess
        can_exec = False
        try:
            result = subprocess.run(['echo', 'test'],
                                  capture_output=True, timeout=1)
            can_exec = result.returncode == 0
        except:
            pass

        info["can_subprocess"] = can_exec
        self.ctx.post("bot", {"type": "process", **info})

    def probe_permissions(self):
        tests = {
            "read_etc_passwd": os.access('/etc/passwd', os.R_OK),
            "read_root": os.access('/', os.R_OK),
            "write_tmp": os.access('/tmp', os.W_OK),
            "write_home": os.access(os.path.expanduser('~'), os.W_OK),
        }

        self.ctx.post("bot", {"type": "permissions", "tests": tests})


# EvalShellBot - Attempts to use eval/exec and private attributes
import sys, io, traceback

class EvalShellBot:
    def __init__(self, ctx, params):
        self.ctx = ctx
        self.params = params
        self.globals = {"ctx": ctx, "__builtins__": __builtins__}

    def on_init(self):
        self.ctx.post("bot", {
            "type": "ready",
            "message": "EvalShell ready! Prefix commands with '>' to eval Python code. '>>' for exec."
        })

    def on_message(self, msg):
        if msg.get("kind") != "user":
            return

        body = msg.get("body", {})
        text = body.get("text", "").strip()

        if text.startswith(">>"):
            # Exec mode
            code = text[2:].strip()
            self._exec_code(code)
        elif text.startswith(">"):
            # Eval mode
            code = text[1:].strip()
            self._eval_code(code)

    def _eval_code(self, code):
        stdout = io.StringIO()
        stderr = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout
            sys.stderr = stderr

            result = eval(code, self.globals)

            sys.stdout = old_stdout
            sys.stderr = old_stderr

            self.ctx.post("bot", {
                "type": "eval_result",
                "code": code,
                "result": repr(result),
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue()
            })
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            self.ctx.post("bot", {
                "type": "eval_error",
                "code": code,
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def _exec_code(self, code):
        stdout = io.StringIO()
        stderr = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout
            sys.stderr = stderr

            exec(code, self.globals)

            sys.stdout = old_stdout
            sys.stderr = old_stderr

            self.ctx.post("bot", {
                "type": "exec_result",
                "code": code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue()
            })
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            self.ctx.post("bot", {
                "type": "exec_error",
                "code": code,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
