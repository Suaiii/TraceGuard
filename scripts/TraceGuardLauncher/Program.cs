using System.Diagnostics;

static string? FindPython(string root)
{
    var candidates = new List<string>();
    var configured = Environment.GetEnvironmentVariable("TRACEGUARD_PYTHON");
    if (!string.IsNullOrWhiteSpace(configured)) candidates.Add(configured);
    candidates.Add(Path.Combine(root, ".venv", "Scripts", "python.exe"));
    candidates.Add(Path.Combine(root, "venv", "Scripts", "python.exe"));
    candidates.Add("python.exe");
    foreach (var candidate in candidates)
    {
        if (candidate == "python.exe" || File.Exists(candidate)) return candidate;
    }
    return null;
}

var launcherRoot = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
var projectRoot = Directory.Exists(Path.Combine(launcherRoot, "TraceGuard"))
    ? Path.Combine(launcherRoot, "TraceGuard")
    : launcherRoot;
var server = Path.Combine(projectRoot, "server.py");
if (!File.Exists(server))
{
    Console.Error.WriteLine("[TraceGuard] 未找到 TraceGuard\\server.py。请保持 TraceGuard.exe 与 TraceGuard 运行目录在同一目录。");
    return 1;
}

var python = FindPython(projectRoot);
if (python is null)
{
    Console.Error.WriteLine("[TraceGuard] 未找到 Python。请安装 Python 3.10+，或设置 TRACEGUARD_PYTHON 环境变量。");
    return 1;
}

var arguments = new List<string> { "server.py" };
arguments.AddRange(args);
var startInfo = new ProcessStartInfo
{
    FileName = python,
    WorkingDirectory = projectRoot,
    UseShellExecute = false,
    Arguments = string.Join(" ", arguments.Select(QuoteArgument)),
};

Console.WriteLine($"[TraceGuard] 启动目录: {projectRoot}");
Console.WriteLine($"[TraceGuard] Python: {python}");
Console.WriteLine("[TraceGuard] 服务启动后访问 http://127.0.0.1:8000/");
using var process = Process.Start(startInfo);
if (process is null)
{
    Console.Error.WriteLine("[TraceGuard] 无法启动 Python 进程。");
    return 1;
}
process.WaitForExit();
return process.ExitCode;

static string QuoteArgument(string value)
{
    if (value.Length == 0) return "\"\"";
    if (!value.Any(char.IsWhiteSpace) && !value.Contains('"')) return value;
    return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
}
