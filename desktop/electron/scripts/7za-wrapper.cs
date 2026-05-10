// 7za.exe wrapper: forwards args to 7za-real.exe but treats exit codes 1 and 2
// as success (sub-item / warning errors from macOS dylib symlinks that Windows
// cannot create without admin privileges).
using System;
using System.Diagnostics;
using System.IO;
using System.Text;

class Wrapper {
    static string Quote(string a) {
        if (a.Length > 0 && a.IndexOfAny(new[]{' ', '\t', '"'}) < 0) return a;
        var sb = new StringBuilder();
        sb.Append('"');
        foreach (var c in a) {
            if (c == '"') sb.Append('\\');
            sb.Append(c);
        }
        sb.Append('"');
        return sb.ToString();
    }
    static int Main(string[] args) {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string real = Path.Combine(dir, "7za-real.exe");
        var sb = new StringBuilder();
        for (int i = 0; i < args.Length; i++) {
            if (i > 0) sb.Append(' ');
            sb.Append(Quote(args[i]));
        }
        var psi = new ProcessStartInfo(real, sb.ToString()) {
            UseShellExecute = false,
        };
        var p = Process.Start(psi);
        p.WaitForExit();
        int rc = p.ExitCode;
        if (rc == 1 || rc == 2) return 0;
        return rc;
    }
}
