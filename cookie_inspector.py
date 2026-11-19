import os
import json
import csv
import time
import threading
from datetime import datetime
from tkinter import filedialog, ttk, messagebox
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class TkBase(ctk.CTk, TkinterDnD.DnDWrapper if DND_AVAILABLE else object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)


class LocalCookieExpirationApp(TkBase):
    def __init__(self):
        super().__init__()

        self.title("Local Cookie Expiration Inspector (Offline)")
        self.geometry("1050x720")
        self.minsize(900, 620)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.bg_card = "#1e1e24"
        self.color_green = "#2ecc71"
        self.color_red = "#e74c3c"
        self.color_yellow = "#f39c12"
        self.color_accent = "#3b8ed0"

        self.results = []
        self.is_scanning = False

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dashboard_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        for i in range(4):
            self.dashboard_frame.grid_columnconfigure(i, weight=1)

        self.card_total = self._create_stat_card(self.dashboard_frame, 0, "Gefundene Einträge", "0", "#ffffff")
        self.card_valid = self._create_stat_card(self.dashboard_frame, 1, "Ablauf in Zukunft", "0", self.color_green)
        self.card_expired = self._create_stat_card(self.dashboard_frame, 2, "Abgelaufen", "0", self.color_red)
        self.card_unknown = self._create_stat_card(self.dashboard_frame, 3, "Unbekannt / Session", "0", self.color_yellow)

        self.drop_frame = ctk.CTkFrame(
            self,
            fg_color=self.bg_card,
            corner_radius=12,
            border_width=2,
            border_color="#33333d"
        )
        self.drop_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.drop_frame.grid_columnconfigure(0, weight=1)

        dnd_hint = "Ordner oder Dateien hierher ziehen" if DND_AVAILABLE else "Ordner oder Dateien auswählen (für Drag & Drop 'tkinterdnd2' installieren)"
        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text=dnd_hint,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.drop_label.grid(row=0, column=0, pady=(18, 6))

        btn_subframe = ctk.CTkFrame(self.drop_frame, fg_color="transparent")
        btn_subframe.grid(row=1, column=0, pady=(0, 12))

        self.btn_select_folder = ctk.CTkButton(
            btn_subframe,
            text="Ordner auswählen",
            command=self.select_folder_dialog,
            corner_radius=8
        )
        self.btn_select_folder.pack(side="left", padx=6)

        self.btn_select_files = ctk.CTkButton(
            btn_subframe,
            text="Dateien auswählen",
            command=self.select_files_dialog,
            fg_color="#2b2b36",
            hover_color="#3a3a48",
            corner_radius=8
        )
        self.btn_select_files.pack(side="left", padx=6)

        self.progress_bar = ctk.CTkProgressBar(self.drop_frame, mode="determinate", height=8)
        self.progress_bar.grid(row=2, column=0, padx=30, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)

        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)

        self.table_frame = ctk.CTkFrame(self, fg_color=self.bg_card, corner_radius=12)
        self.table_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#1e1e24",
            foreground="#e0e0e0",
            fieldbackground="#1e1e24",
            borderwidth=0,
            rowheight=28,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#282832",
            foreground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Treeview", background=[("selected", "#3b8ed0")])

        columns = ("filename", "cookie_type", "exp_date", "remaining", "status")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("filename", text="Dateiname")
        self.tree.heading("cookie_type", text="Cookie-Typ / Format")
        self.tree.heading("exp_date", text="Ablaufdatum")
        self.tree.heading("remaining", text="Verbleibende Dauer")
        self.tree.heading("status", text="Status")

        self.tree.column("filename", width=260, anchor="w")
        self.tree.column("cookie_type", width=180, anchor="w")
        self.tree.column("exp_date", width=160, anchor="center")
        self.tree.column("remaining", width=180, anchor="center")
        self.tree.column("status", width=160, anchor="center")

        self.tree.tag_configure("GRÜN", foreground=self.color_green)
        self.tree.tag_configure("ROT", foreground=self.color_red)
        self.tree.tag_configure("GELB", foreground=self.color_yellow)

        scrollbar = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, padx=(12, 0), pady=12, sticky="nsew")
        scrollbar.grid(row=0, column=1, padx=8, pady=12, sticky="ns")

        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew")

        self.info_label = ctk.CTkLabel(
            self.footer_frame,
            text="Hinweis: Reine Offline-Prüfung der Zeitstempel. Keine Kontovalidierung oder Speicherung von Token-Werten.",
            text_color="#888894",
            font=ctk.CTkFont(size=12)
        )
        self.info_label.pack(side="left")

        self.btn_clear = ctk.CTkButton(
            self.footer_frame,
            text="Liste leeren",
            fg_color="#3a3a48",
            hover_color="#4a4a5a",
            width=110,
            command=self.clear_results
        )
        self.btn_clear.pack(side="right", padx=(6, 0))

        self.btn_export_json = ctk.CTkButton(
            self.footer_frame,
            text="JSON Export",
            width=110,
            command=lambda: self.export_results("json")
        )
        self.btn_export_json.pack(side="right", padx=6)

        self.btn_export_txt = ctk.CTkButton(
            self.footer_frame,
            text="TXT Export",
            width=110,
            command=lambda: self.export_results("txt")
        )
        self.btn_export_txt.pack(side="right", padx=6)

        self.btn_export_csv = ctk.CTkButton(
            self.footer_frame,
            text="CSV Export",
            width=110,
            command=lambda: self.export_results("csv")
        )
        self.btn_export_csv.pack(side="right", padx=6)

    def _create_stat_card(self, parent, col, title, initial_val, color):
        card = ctk.CTkFrame(parent, fg_color=self.bg_card, corner_radius=12)
        card.grid(row=0, column=col, padx=6, sticky="ew")

        lbl_title = ctk.CTkLabel(card, text=title, text_color="#a0a0ab", font=ctk.CTkFont(size=12))
        lbl_title.pack(pady=(12, 2), padx=12)

        lbl_val = ctk.CTkLabel(card, text=initial_val, text_color=color, font=ctk.CTkFont(size=24, weight="bold"))
        lbl_val.pack(pady=(0, 12), padx=12)
        return lbl_val

    def _on_drop(self, event):
        if self.is_scanning:
            return
        raw_paths = self.tk.splitlist(event.data)
        self.start_analysis(raw_paths)

    def select_folder_dialog(self):
        if self.is_scanning:
            return
        folder = filedialog.askdirectory(title="Ordner mit Cookie-Dateien auswählen")
        if folder:
            self.start_analysis([folder])

    def select_files_dialog(self):
        if self.is_scanning:
            return
        files = filedialog.askopenfilenames(
            title="Cookie-Dateien auswählen",
            filetypes=[("Unterstützte Dateien", "*.txt *.json *.cookies"), ("Alle Dateien", "*.*")]
        )
        if files:
            self.start_analysis(list(files))

    def start_analysis(self, input_paths):
        self.is_scanning = True
        self.progress_bar.set(0)
        self.drop_label.configure(text="Durchsuche Dateien...")
        threading.Thread(target=self._scan_worker, args=(input_paths,), daemon=True).start()

    def _scan_worker(self, input_paths):
        target_files = []
        supported_ext = {".txt", ".json", ".cookies"}

        for path in input_paths:
            if os.path.isfile(path):
                target_files.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in supported_ext:
                            target_files.append(os.path.join(root, f))

        total_files = len(target_files)
        if total_files == 0:
            self.after(0, lambda: self._finish_scan())
            return

        new_entries = []
        for idx, file_path in enumerate(target_files):
            parsed = self._parse_cookie_file(file_path)
            new_entries.extend(parsed)
            progress = (idx + 1) / total_files
            self.after(0, lambda p=progress: self.progress_bar.set(p))

        self.after(0, lambda: self._update_ui_with_results(new_entries))

    def _parse_cookie_file(self, file_path):
        filename = os.path.basename(file_path)
        entries = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()

            if not content:
                return [{
                    "filename": filename,
                    "cookie_type": "Leer",
                    "exp_date": "-",
                    "remaining": "-",
                    "status": "GELB"
                }]

            if content.startswith("[") or content.startswith("{"):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        data = data.get("cookies", [data])
                    if isinstance(data, list):
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            c_name = str(item.get("name", "JSON-Cookie"))[:30]
                            exp_raw = item.get("expirationDate", item.get("expires", item.get("expiry")))
                            entries.append(self._evaluate_timestamp(filename, f"JSON ({c_name})", exp_raw))
                        if entries:
                            return entries
                except json.JSONDecodeError:
                    pass

            lines = content.splitlines()
            found_netscape = False
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") and not line.startswith("#HttpOnly_"):
                    continue
                if line.startswith("#HttpOnly_"):
                    line = line[len("#HttpOnly_"):]

                parts = line.split("\t")
                if len(parts) >= 7:
                    found_netscape = True
                    domain = parts[0][:20]
                    exp_raw = parts[4]
                    c_name = parts[5][:25]
                    entries.append(
                        self._evaluate_timestamp(filename, f"Netscape ({c_name} @ {domain})", exp_raw)
                    )

            if found_netscape:
                return entries

            return [{
                "filename": filename,
                "cookie_type": "Unbekanntes Format",
                "exp_date": "-",
                "remaining": "Nicht lesbar",
                "status": "GELB"
            }]

        except Exception:
            return [{
                "filename": filename,
                "cookie_type": "Lesefehler",
                "exp_date": "-",
                "remaining": "Beschädigte Datei",
                "status": "GELB"
            }]

    def _evaluate_timestamp(self, filename, cookie_type, exp_raw):
        now = time.time()

        if exp_raw is None or str(exp_raw).strip() == "":
            return {
                "filename": filename,
                "cookie_type": cookie_type,
                "exp_date": "Kein Datum",
                "remaining": "Session / Unbekannt",
                "status": "GELB"
            }

        try:
            exp_ts = float(exp_raw)
            if exp_ts > 1e11:
                exp_ts /= 1000.0

            if exp_ts <= 0:
                return {
                    "filename": filename,
                    "cookie_type": cookie_type,
                    "exp_date": "Session-Cookie",
                    "remaining": "Endet mit Sitzung",
                    "status": "GELB"
                }

            dt_str = datetime.fromtimestamp(exp_ts).strftime("%Y-%m-%d %H:%M")
            diff = exp_ts - now

            if diff > 0:
                days = int(diff // 86400)
                hours = int((diff % 86400) // 3600)
                rem_str = f"{days}d {hours}h" if days > 0 else f"{hours}h {int((diff % 3600) // 60)}m"
                status = "GRÜN"
            else:
                abs_diff = abs(diff)
                days = int(abs_diff // 86400)
                rem_str = f"Vor {days}d abgelaufen" if days > 0 else "Heute abgelaufen"
                status = "ROT"

            return {
                "filename": filename,
                "cookie_type": cookie_type,
                "exp_date": dt_str,
                "remaining": rem_str,
                "status": status
            }

        except (ValueError, OSError, OverflowError):
            return {
                "filename": filename,
                "cookie_type": cookie_type,
                "exp_date": "Ungültig",
                "remaining": "Unbekannt",
                "status": "GELB"
            }

    def _update_ui_with_results(self, new_entries):
        for entry in new_entries:
            self.results.append(entry)
            self.tree.insert(
                "",
                "end",
                values=(
                    entry["filename"],
                    entry["cookie_type"],
                    entry["exp_date"],
                    entry["remaining"],
                    entry["status"]
                ),
                tags=(entry["status"],)
            )

        self._refresh_counters()
        self._finish_scan()

    def _finish_scan(self):
        self.is_scanning = False
        dnd_hint = "Ordner oder Dateien hierher ziehen" if DND_AVAILABLE else "Ordner oder Dateien auswählen"
        self.drop_label.configure(text=dnd_hint)

    def _refresh_counters(self):
        total = len(self.results)
        green = sum(1 for r in self.results if r["status"] == "GRÜN")
        red = sum(1 for r in self.results if r["status"] == "ROT")
        yellow = sum(1 for r in self.results if r["status"] == "GELB")

        self.card_total.configure(text=str(total))
        self.card_valid.configure(text=str(green))
        self.card_expired.configure(text=str(red))
        self.card_unknown.configure(text=str(yellow))

    def clear_results(self):
        self.results.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_counters()
        self.progress_bar.set(0)

    def export_results(self, fmt):
        if not self.results:
            messagebox.showinfo("Export", "Keine Ergebnisse zum Exportieren vorhanden.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()}-Datei", f"*.{fmt}")]
        )
        if not file_path:
            return

        try:
            if fmt == "csv":
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Dateiname", "Cookie-Typ", "Ablaufdatum", "Verbleibende Dauer", "Status"])
                    for r in self.results:
                        writer.writerow([r["filename"], r["cookie_type"], r["exp_date"], r["remaining"], r["status"]])

            elif fmt == "txt":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("COOKIE ABLAUF-ANALYSE (OHNE GEHEIME TOKEN-WERTE)\n")
                    f.write("=" * 65 + "\n")
                    for r in self.results:
                        f.write(
                            f"[{r['status']}] {r['filename']} | {r['cookie_type']} | "
                            f"Ablauf: {r['exp_date']} ({r['remaining']})\n"
                        )

            elif fmt == "json":
                summary = {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": {
                        "total": len(self.results),
                        "future_expiration": sum(1 for r in self.results if r["status"] == "GRÜN"),
                        "expired": sum(1 for r in self.results if r["status"] == "ROT"),
                        "unknown_or_session": sum(1 for r in self.results if r["status"] == "GELB"),
                    },
                    "entries": self.results
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Export erfolgreich", f"Ergebnisliste wurde gespeichert unter:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export-Fehler", f"Fehler beim Speichern:\n{e}")


if __name__ == "__main__":
    app = LocalCookieExpirationApp()
    app.mainloop()