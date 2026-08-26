#include <windows.h>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static std::wstring quote_arg(const std::wstring& value) {
    if (value.empty()) return L"\"\"";
    bool needs_quotes = value.find_first_of(L" \t\"") != std::wstring::npos;
    if (!needs_quotes) return value;
    std::wstring out = L"\"";
    for (wchar_t c : value) {
        if (c == L'\"') out += L'\\';
        out += c;
    }
    out += L"\"";
    return out;
}

static std::wstring exe_dir() {
    std::vector<wchar_t> buffer(MAX_PATH);
    DWORD length = 0;
    do {
        buffer.resize(buffer.size() * 2);
        length = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    } while (length == buffer.size());
    if (length == 0) return L".";
    return fs::path(std::wstring(buffer.data(), length)).parent_path().wstring();
}

static std::wstring env_value(const wchar_t* name) {
    DWORD size = GetEnvironmentVariableW(name, nullptr, 0);
    if (size == 0) return L"";
    std::wstring result(size, L'\0');
    GetEnvironmentVariableW(name, result.data(), size);
    result.resize(wcslen(result.c_str()));
    return result;
}

int wmain(int argc, wchar_t* argv[]) {
    SetConsoleTitleW(L"TraceGuard:面向社交媒体网络传播的 可解释 AIGC 图像取证平台");
    fs::path root = exe_dir();
    fs::path project = fs::exists(root / L"TraceGuard" / L"server.py") ? root / L"TraceGuard" : root;
    fs::path server = project / L"server.py";
    if (!fs::exists(server)) {
        std::wcerr << L"[TraceGuard] 未找到 TraceGuard\\server.py。请保持 TraceGuard.exe 与 TraceGuard 运行目录在同一目录。\n";
        return 1;
    }

    std::wstring python = env_value(L"TRACEGUARD_PYTHON");
    if (python.empty()) {
        fs::path local = project / L".venv" / L"Scripts" / L"python.exe";
        fs::path venv = project / L"venv" / L"Scripts" / L"python.exe";
        if (fs::exists(local)) python = local.wstring();
        else if (fs::exists(venv)) python = venv.wstring();
        else python = L"python.exe";
    }

    std::wstring command = quote_arg(python) + L" server.py";
    for (int i = 1; i < argc; ++i) command += L" " + quote_arg(argv[i]);
    std::vector<wchar_t> command_buffer(command.begin(), command.end());
    command_buffer.push_back(L'\0');
    std::wstring working = project.wstring();
    std::wcout << L"[TraceGuard] 启动目录: " << working << L"\n";
    std::wcout << L"[TraceGuard] 服务启动后访问 http://127.0.0.1:8000/\n";

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    BOOL ok = CreateProcessW(nullptr, command_buffer.data(), nullptr, nullptr, TRUE, 0, nullptr,
                             working.c_str(), &startup, &process);
    if (!ok) {
        std::wcerr << L"[TraceGuard] 无法启动 Python 进程，错误码: " << GetLastError() << L"\n";
        return 1;
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exit_code = 1;
    GetExitCodeProcess(process.hProcess, &exit_code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return static_cast<int>(exit_code);
}
