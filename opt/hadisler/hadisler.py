import sys
import sqlite3
import os
import re
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QListWidget, QTextEdit, QLabel, 
                             QSplitter, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QIcon

class HadisUygulamasi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hadis Külliyatı")
        self.showMaximized()
        
        # Dosya Yolları
        self.db_path = os.path.join(os.path.dirname(__file__), "hadisler.db")
        self.config_path = os.path.expanduser("~/.hadisler_config.json")
        
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.settings = {
            "is_dark_mode": False,
            "base_font_size": 12,
            "last_fasil": None,
            "last_konu": None
        }
        
        self.load_settings()
        self.is_dark_mode = self.settings["is_dark_mode"]
        self.base_font_size = self.settings["base_font_size"]
        self.last_selected_konu = self.settings["last_konu"]
        self.search_query = ""

        self.init_ui()
        self.load_fasillar()
        self.apply_theme()
        self.restore_session()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Hadislerde ara...")
        self.search_input.setMinimumWidth(150)
        self.search_input.returnPressed.connect(self.search_hadis)
        
        btn_search = QPushButton("🔍 Ara")
        btn_search.clicked.connect(self.search_hadis)

        btn_font_plus = QPushButton("A+")
        btn_font_plus.clicked.connect(lambda: self.update_font_size(1))
        
        btn_font_minus = QPushButton("A-")
        btn_font_minus.clicked.connect(lambda: self.update_font_size(-1))

        self.btn_copy = QPushButton("📋 Kopyala")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)

        self.btn_theme = QPushButton("🌙 Gece")
        self.btn_theme.clicked.connect(self.toggle_theme)

        top_bar.addWidget(QLabel("<b>HADİS PORTAL</b>"))
        top_bar.addSpacing(20)
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(btn_search)
        top_bar.addStretch()
        top_bar.addWidget(btn_font_minus)
        top_bar.addWidget(btn_font_plus)
        top_bar.addWidget(self.btn_copy)
        top_bar.addWidget(self.btn_theme)
        self.main_layout.addLayout(top_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.fasil_list = QListWidget()
        self.fasil_list.setObjectName("fasilList")
        self.fasil_list.setWordWrap(True)
        self.fasil_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.fasil_list.itemClicked.connect(self.load_konular)
        
        self.konu_list = QListWidget()
        self.konu_list.setObjectName("konuList")
        self.konu_list.setWordWrap(True)
        self.konu_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.konu_list.itemClicked.connect(self.load_hadis_detay)

        self.detail_view = QTextEdit()
        self.detail_view.setObjectName("hadisView")
        self.detail_view.setReadOnly(True)
        self.detail_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.detail_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.splitter.addWidget(self.create_panel("Fasıllar", self.fasil_list))
        self.splitter.addWidget(self.create_panel("Konular", self.konu_list))
        self.splitter.addWidget(self.create_panel("Hadis Metni ve Şerhi", self.detail_view))
        
        self.splitter.setSizes([300, 300, 800])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 4)
        
        self.main_layout.addWidget(self.splitter)

    def create_panel(self, title, widget):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.addWidget(QLabel(f"<b>{title}</b>"))
        lay.addWidget(widget)
        return container

    def apply_theme(self):
        mint = "#45ad1d"
        main_bg = "#e2e8e4"
        fasil_bg = "#d1d8d5"
        konu_bg = "#c5cdca"
        light_silver = "#f0f2f1"
        
        if self.is_dark_mode:
            bg, p_bg, txt, border = "#2f2f2f", "#383838", "#e0e0e0", "#444"
            f_bg, k_bg, h_bg = "#333", "#3a3a3a", "#2b2b2b"
            self.btn_theme.setText("☀️ Gündüz")
        else:
            bg, p_bg, txt, border = main_bg, "#ffffff", "#2c3e50", "#b0bbba"
            f_bg, k_bg, h_bg = fasil_bg, konu_bg, light_silver
            self.btn_theme.setText("🌙 Gece")
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg}; color: {txt}; }}
            QListWidget#fasilList {{ background-color: {f_bg}; border: 1px solid {border}; border-radius: 6px; color: {txt}; font-weight: bold; font-size: 14px; outline: none; }}
            QListWidget#konuList {{ background-color: {k_bg}; border: 1px solid {border}; border-radius: 6px; color: {txt}; font-weight: bold; font-size: 14px; outline: none; }}
            QTextEdit#hadisView {{ background-color: {h_bg}; border: 1px solid {border}; border-radius: 6px; color: {txt}; padding: 10px; }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid {bg}; }}
            QListWidget::item:selected {{ background-color: {mint}; color: white; border-radius: 4px; }}
            QPushButton {{ background-color: {p_bg}; padding: 6px 14px; border: 1px solid {border}; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {mint}; color: white; }}
            QLineEdit {{ background-color: {p_bg}; border: 1px solid {border}; border-radius: 4px; padding: 4px; }}
        """)
        if self.last_selected_konu: self.display_content(self.last_selected_konu)
        self.save_settings()

    def load_fasillar(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT fasil FROM hadisler WHERE fasil IS NOT NULL ORDER BY _id")
            self.fasil_list.clear()
            for row in cursor.fetchall(): self.fasil_list.addItem(row[0])
            conn.close()
        except: pass

    def load_konular(self, item):
        self.konu_list.clear()
        self.settings["last_fasil"] = item.text()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT konu FROM hadisler WHERE fasil = ? ORDER BY _id", (item.text(),))
        for row in cursor.fetchall(): self.konu_list.addItem(row[0])
        conn.close()
        self.save_settings()

    def load_hadis_detay(self, item):
        self.search_query = ""
        self.last_selected_konu = item.text()
        self.settings["last_konu"] = item.text()
        self.display_content(self.last_selected_konu)
        self.save_settings()

    def search_hadis(self):
        self.search_query = self.search_input.text()
        if self.search_query: self.display_content(self.search_query, True)

    def highlight_text(self, text):
        if not self.search_query: return text
        try:
            pattern = re.compile(re.escape(self.search_query), re.IGNORECASE)
            return pattern.sub(lambda m: f"<span style='color: #ff0000; font-weight: bold;'>{m.group(0)}</span>", text)
        except: return text

    def display_content(self, term, is_search=False):
        self.detail_view.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = "SELECT h._id, h.arabca, h.hadis, h.ravi, s.serh FROM hadisler h LEFT JOIN serh s ON h.serh1_id = s._id WHERE "
            if is_search:
                query += "(h.hadis LIKE ? OR h.arabca LIKE ? OR h._id = ?)"
                params = (f'%{term}%', f'%{term}%', term)
            else:
                query += "h.konu = ?"
                params = (term,)
            
            cursor.execute(query, params)
            res = cursor.fetchall()
            
            mint = "#45ad1d" 
            arap_kirmizi = "#e74c3c"
            t_color = "#333333" if not self.is_dark_mode else "#dddddd"
            sh_bg = "#ffffff" if not self.is_dark_mode else "#424242"

            html = ""
            for r in res:
                h_f, s_f = self.base_font_size, self.base_font_size - 1
                arap_f = h_f + 10 
                hadis_m = self.highlight_text(r[2])
                serh_m = self.highlight_text(r[4] if r[4] else 'Bu hadis için şerh kaydı bulunamadı.')
                
                html += f"""
                <div style='margin-bottom: 35px; word-wrap: break-word;'>
                    <div style='color: {mint}; font-weight: bold; font-size: 12pt; text-align: center;'>
                        — Hadis No: {r[0]} —
                    </div>
                    
                    <br>
                    
                    <div style='direction: rtl; font-size: {arap_f}pt; color: {arap_kirmizi}; font-family: "Amiri", serif; line-height: 1.4;'>
                        {r[1]}
                    </div>
                    
                    <p style='color: #7f8c8d; font-size: 10pt; margin-top: 8px; margin-bottom: 5px;'><b>Ravi:</b> {r[3]}</p>
                    <p style='font-size: {h_f}pt; line-height: 1.5; color: {t_color};'><b>Hadis: {hadis_m}</b></p>
                    
                    <div style='background-color: {sh_bg}; padding: 18px; border-left: 4px solid {mint}; margin-top: 15px; border-radius: 4px; border: 1px solid #d1d8d5;'>
                        <b style='color: {mint}; font-size: 9pt;'>ŞERH</b><br>
                        <div style='font-size: {s_f}pt; line-height: 1.5; color: {t_color}; margin-top: 8px;'>{serh_m}</div>
                    </div>
                    <hr style='border: 0; border-top: 1px solid #d1d8d5; margin-top: 25px;'>
                </div>"""
            self.detail_view.setHtml(html)
            conn.close()
        except: pass

    def update_font_size(self, step):
        self.base_font_size = max(8, min(self.base_font_size + step, 30))
        self.settings["base_font_size"] = self.base_font_size
        if self.last_selected_konu: self.display_content(self.last_selected_konu)
        self.save_settings()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def load_settings(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except: pass

    def save_settings(self):
        self.settings["is_dark_mode"] = self.is_dark_mode
        self.settings["base_font_size"] = self.base_font_size
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except: pass

    def restore_session(self):
        last_fasil = self.settings.get("last_fasil")
        if last_fasil:
            items = self.fasil_list.findItems(last_fasil, Qt.MatchFlag.MatchExactly)
            if items:
                self.fasil_list.setCurrentItem(items[0])
                self.load_konular(items[0])
                last_konu = self.settings.get("last_konu")
                if last_konu:
                    k_items = self.konu_list.findItems(last_konu, Qt.MatchFlag.MatchExactly)
                    if k_items:
                        self.konu_list.setCurrentItem(k_items[0])
                        self.load_hadis_detay(k_items[0])

    def copy_to_clipboard(self):
        QGuiApplication.clipboard().setText(self.detail_view.toPlainText())
        self.btn_copy.setText("✅")
        QTimer.singleShot(1000, lambda: self.btn_copy.setText("📋 Kopyala"))

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HadisUygulamasi()
    window.show()
    sys.exit(app.exec())