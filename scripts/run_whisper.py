import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import time
import atexit
import sys

class TranscriptionCancelled(Exception):
    """Custom exception to signal transcription cancellation."""
    pass

class AudioProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Processor - Обработка Аудио/Видео")
        self.root.geometry("800x750")
        
        # Определяем базовую папку (родительская от scripts)
        self.base_dir = Path(__file__).parent.parent
        
        # Создаем рабочие папки
        self.input_dir = self.base_dir / "input"
        self.audio_dir = self.base_dir / "audio" 
        self.transcripts_dir = self.base_dir / "transcripts"
        self.output_dir = self.base_dir / "output"
        
        # Создаем папки если их нет
        for dir_path in [self.input_dir, self.audio_dir, self.transcripts_dir, self.output_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.current_work_dir = self.input_dir  # По умолчанию работаем с input
        
        # Список активных процессов и активный поток для возможности их остановки
        self.active_processes = []
        self.current_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        
        # Регистрируем обработчики закрытия
        self.register_cleanup_handlers()
        
        self.setup_ui()
        self.refresh_files()
        
        # Запускаем проверку системы в отдельном потоке
        threading.Thread(target=self.check_system_requirements, daemon=True).start()
        
    def register_cleanup_handlers(self):
        """Регистрация обработчиков для корректного завершения"""
        try:
            # При закрытии окна
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # При завершении программы
            atexit.register(self.cleanup_on_exit)
        except Exception as e:
            print(f"Ошибка регистрации обработчиков: {e}")
            
    def on_closing(self):
        """Обработчик закрытия окна"""
        try:
            self.cleanup_on_exit()
        except:
            pass
        self.root.destroy()
        
    def cleanup_on_exit(self):
        """Очистка при завершении программы"""
        try:
            # Останавливаем все активные процессы
            if hasattr(self, 'active_processes') and self.active_processes:
                for process in self.active_processes[:]:
                    try:
                        if process.poll() is None:
                            process.terminate()
                            process.wait(timeout=2)
                    except:
                        pass
                        
        except Exception as e:
            print(f"Ошибка при очистке: {e}")
            
    def setup_ui(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Выбор рабочей папки
        dir_frame = ttk.LabelFrame(main_frame, text="Рабочие папки", padding="10")
        dir_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Радиокнопки для выбора папки
        self.work_dir_var = tk.StringVar(value="input")
        
        ttk.Radiobutton(dir_frame, text="📹 Видеофайлы (input)", 
                       variable=self.work_dir_var, value="input",
                       command=self.change_work_dir).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Radiobutton(dir_frame, text="🎵 Аудиофайлы (audio)", 
                       variable=self.work_dir_var, value="audio",
                       command=self.change_work_dir).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Radiobutton(dir_frame, text="📄 Расшифровки (transcripts)", 
                       variable=self.work_dir_var, value="transcripts",
                       command=self.change_work_dir).grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(dir_frame, text="🎨 Результаты (output)", 
                       variable=self.work_dir_var, value="output",
                       command=self.change_work_dir).grid(row=0, column=3, sticky=tk.W)
        
        ttk.Button(dir_frame, text="Открыть папку", command=self.open_current_directory).grid(row=0, column=4, sticky=tk.E, padx=(20, 0))
        
        dir_frame.columnconfigure(4, weight=1)
        
        # Текущая папка
        self.current_dir_var = tk.StringVar(value=str(self.current_work_dir))
        ttk.Label(main_frame, text="Текущая папка:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main_frame, textvariable=self.current_dir_var, state="readonly", width=80).grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Список файлов
        ttk.Label(main_frame, text="Файлы в папке:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        files_frame = ttk.Frame(main_frame)
        files_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.files_tree = ttk.Treeview(files_frame, columns=('type', 'size'), show='tree headings', height=10)
        self.files_tree.heading('#0', text='Файл')
        self.files_tree.heading('type', text='Тип')
        self.files_tree.heading('size', text='Размер')
        
        self.files_tree.column('#0', width=400)
        self.files_tree.column('type', width=100)
        self.files_tree.column('size', width=100)
        
        scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar.set)
        
        self.files_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        ttk.Button(main_frame, text="Обновить список", command=self.refresh_files).grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        # Кнопки действий
        actions_frame = ttk.LabelFrame(main_frame, text="Действия", padding="10")
        actions_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Кнопки действий
        ttk.Button(actions_frame, text="Извлечь аудио из видео", 
                  command=self.extract_audio, width=20).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(actions_frame, text="Транскрибировать аудио", 
                  command=self.transcribe_audio, width=20).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(actions_frame, text="Полный цикл", 
                  command=self.full_cycle, width=15).grid(row=0, column=2, padx=(5, 5))
        ttk.Button(actions_frame, text="⏹ Остановить", 
                  command=self.stop_all_processes, width=12).grid(row=0, column=3, padx=(5, 0))
        
        actions_frame.columnconfigure(4, weight=1)
        
        # Прогресс-бар
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))
        
        self.progress_var = tk.StringVar(value="Готов к работе")
        self.progress_label = ttk.Label(self.progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(2, 0))
        
        self.progress_frame.columnconfigure(0, weight=1)
        
        # Лог
        log_label_frame = ttk.Frame(main_frame)
        log_label_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))
        
        ttk.Label(log_label_frame, text="Лог выполнения:").grid(row=0, column=0, sticky=tk.W)
        
        log_buttons_frame = ttk.Frame(log_label_frame)
        log_buttons_frame.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Button(log_buttons_frame, text="Копировать всё", command=self.copy_all_log, width=12).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(log_buttons_frame, text="Очистить", command=self.clear_log, width=10).grid(row=0, column=1)
        
        log_label_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80, wrap=tk.WORD)
        self.log_text.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Контекстное меню для лога
        self.log_context_menu = tk.Menu(self.root, tearoff=0)
        self.log_context_menu.add_command(label="Копировать", command=self.copy_selected_log)
        self.log_context_menu.add_command(label="Копировать всё", command=self.copy_all_log)
        self.log_context_menu.add_separator()
        self.log_context_menu.add_command(label="Очистить", command=self.clear_log)
        
        # Привязка контекстного меню
        self.log_text.bind("<Button-3>", self.show_log_context_menu)
        
        # Настройка весов для растягивания
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(9, weight=1)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def check_system_requirements(self):
        """Проверка системных требований при запуске"""
        try:
            time.sleep(0.5)
            
            self.log("==========================================")
            self.log("      ПРОВЕРКА СИСТЕМЫ")
            self.log("==========================================")
            
            # Проверка CUDA
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_name = torch.cuda.get_device_name(0)
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory // 1024**3
                    self.log(f"✅ CUDA доступна")
                    self.log(f"🎮 GPU: {gpu_name}")
                    self.log(f"💾 Видеопамять: {gpu_memory} ГБ")
                    self.log("⚡ Транскрипция будет быстрой")
                else:
                    self.log("⚠️ CUDA недоступна")
                    self.log("🐌 Транскрипция будет на CPU (медленно)")
            except ImportError:
                self.log("❌ PyTorch не установлен")
            except Exception as e:
                self.log(f"❓ Ошибка проверки CUDA: {e}")
            
            # Проверка FFmpeg
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.log("✅ FFmpeg доступен")
                    self.log("🎬 Извлечение аудио будет работать")
                else:
                    self.log("❌ FFmpeg установлен, но работает неправильно")
            except FileNotFoundError:
                self.log("❌ FFmpeg не найден в PATH")
            except Exception as e:
                self.log(f"❓ Ошибка проверки FFmpeg: {e}")
            
            # Проверка Whisper
            try:
                import whisper
                self.log("✅ Whisper установлен")
                available_models = whisper.available_models()
                if 'large-v3' in available_models:
                    self.log("🎯 Модель large-v3 доступна")
                else:
                    self.log("⚠️ Модель large-v3 не найдена")
            except ImportError:
                self.log("❌ Whisper не установлен")
            except Exception as e:
                self.log(f"❓ Ошибка проверки Whisper: {e}")
            
            self.log("==========================================")
            self.log("Система готова к работе!")
            self.log("")
            
        except Exception as e:
            self.log(f"Ошибка проверки системы: {e}")
        
    def change_work_dir(self):
        dir_name = self.work_dir_var.get()
        if dir_name == "input":
            self.current_work_dir = self.input_dir
        elif dir_name == "audio":
            self.current_work_dir = self.audio_dir
        elif dir_name == "transcripts":
            self.current_work_dir = self.transcripts_dir
        elif dir_name == "output":
            self.current_work_dir = self.output_dir
            
        self.current_dir_var.set(str(self.current_work_dir))
        self.refresh_files()
        
    def open_current_directory(self):
        os.startfile(self.current_work_dir)
        
    def stop_all_processes(self):
        """Остановка всех активных процессов"""
        has_threads = self.current_thread and self.current_thread.is_alive()
        has_processes = bool(self.active_processes)
        if not (has_threads or has_processes):
            self.log("⚠️ Нет активных процессов для остановки")
            return

        self.stop_event.set()
        stopped_count = 0

        if has_processes:
            self.log("🛑 Останавливаем активные процессы...")
            for process in self.active_processes[:]:
                try:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        stopped_count += 1
                    self.active_processes.remove(process)
                except Exception as e:
                    self.log(f"Ошибка при остановке процесса: {e}")

        if has_threads:
            self.log("🛑 Останавливаем текущую задачу...")
            # Поток завершится после обработки stop_event
            self.current_thread = None

        self.stop_progress("Процессы остановлены")
        if stopped_count:
            self.log(f"✅ Остановлено процессов: {stopped_count}")
            
    def cleanup_finished_processes(self):
        """Удаление завершенных процессов из списка"""
        self.active_processes = [p for p in self.active_processes if p.poll() is None]
        
    def start_progress(self, message, determinate=False):
        self.progress_var.set(message)
        if determinate:
            self.progress_bar.config(mode='determinate', maximum=100, value=0)
        else:
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)

    def stop_progress(self, message="Готов к работе"):
        self.progress_bar.stop()
        self.progress_bar.config(mode='indeterminate', value=0)
        self.progress_var.set(message)
        
    def log(self, message):
        try:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.root.update()
        except:
            print(message)  # Fallback на print если GUI недоступен
        
    def show_log_context_menu(self, event):
        try:
            self.log_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_context_menu.grab_release()
            
    def copy_selected_log(self):
        try:
            selected_text = self.log_text.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.log("📋 Выделенный текст скопирован в буфер обмена")
        except tk.TclError:
            self.copy_all_log()
            
    def copy_all_log(self):
        log_content = self.log_text.get(1.0, tk.END).strip()
        if log_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.log("📋 Весь лог скопирован в буфер обмена")
        else:
            messagebox.showinfo("Информация", "Лог пуст")
            
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        
    def refresh_files(self):
        self.files_tree.delete(*self.files_tree.get_children())
        
        if not self.current_work_dir.exists():
            return
            
        video_exts = {'.mp4', '.avi', '.mkv', '.mov'}
        audio_exts = {'.m4a', '.wav', '.mp3', '.ogg'}
        text_exts = {'.txt'}
        
        files_with_time = []
        for file_path in self.current_work_dir.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in video_exts or ext in audio_exts or ext in text_exts:
                    mtime = file_path.stat().st_mtime
                    files_with_time.append((file_path, mtime))
        
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        for file_path, _ in files_with_time:
            ext = file_path.suffix.lower()
            size = file_path.stat().st_size
            size_str = f"{size // 1024 // 1024} МБ" if size > 1024*1024 else f"{size // 1024} КБ"
            
            if ext in video_exts:
                file_type = "📹 Видео"
            elif ext in audio_exts:
                file_type = "🎵 Аудио"
            elif ext in text_exts:
                file_type = "📄 Текст"
                
            self.files_tree.insert('', tk.END, text=file_path.name, 
                                 values=(file_type, size_str))
                                     
    def get_selected_file(self):
        selection = self.files_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите файл из списка")
            return None
        return self.files_tree.item(selection[0])['text']
        
    def run_command(self, cmd, cwd=None):
        if cwd is None:
            cwd = self.base_dir
            
        try:
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(cmd, cwd=cwd, shell=True, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.STDOUT,
                                     universal_newlines=True,
                                     encoding='utf-8',
                                     errors='replace',
                                     env=env)
            
            self.active_processes.append(process)
            self.cleanup_finished_processes()
            
            current_progress_line = None
            
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                    
                if process.poll() is not None:
                    break
                    
                if '%|' in line and ('frames/s' in line or 'it/s' in line):
                    if current_progress_line is not None:
                        self.log_text.delete(f"{current_progress_line}.0", f"{current_progress_line + 1}.0")
                    
                    self.log_text.insert(tk.END, f"{line}\n")
                    current_progress_line = int(self.log_text.index(tk.END).split('.')[0]) - 2
                    self.log_text.see(tk.END)
                    self.root.update()
                else:
                    current_progress_line = None
                    self.log(line)
                
            process.wait()
            
            if process in self.active_processes:
                self.active_processes.remove(process)
                
            return process.returncode == 0
        except Exception as e:
            self.log(f"Ошибка: {e}")
            return False

    def run_transcription(self, audio_file: Path):
        progress_line = None
        self.progress_bar.config(mode='determinate', maximum=100, value=0)

        def on_progress(processed, total, elapsed, remaining):
            nonlocal progress_line
            processed = int(processed)
            total_int = int(total) if total else 0
            msg = f"Обработано: {processed}"
            if total:
                msg += f" из {total_int}"
            msg += f" | прошло: {elapsed:.1f}с"
            if remaining is not None:
                msg += f" | осталось: {remaining:.1f}с"
            if progress_line is not None:
                self.log_text.delete(f"{progress_line}.0", f"{progress_line + 1}.0")
            self.log_text.insert(tk.END, msg + "\n")
            progress_line = int(self.log_text.index(tk.END).split('.')[0]) - 2
            self.log_text.see(tk.END)
            self.progress_var.set(f"{processed} из {total_int} обработано")
            self.root.update()
            if total_int:
                self.progress_bar['value'] = processed / total_int * 100
            if self.stop_event.is_set():
                raise TranscriptionCancelled()

        transcribe_file(audio_file, progress_callback=on_progress, stop_event=self.stop_event)
            
    def extract_audio(self):
        selected_file = self.get_selected_file()
        if not selected_file:
            return
            
        input_file = self.input_dir / selected_file
        if not input_file.exists():
            messagebox.showerror("Ошибка", f"Файл не найден в папке input: {selected_file}")
            return
            
        if input_file.suffix.lower() not in {'.mp4', '.avi', '.mkv', '.mov'}:
            messagebox.showerror("Ошибка", "Выберите видеофайл")
            return
            
        output_file = self.audio_dir / f"{input_file.stem}_audio.m4a"
        
        self.log(f"Извлекаем аудио из: {selected_file}")
        self.log(f"Сохраняем в: audio/{output_file.name}")
        self.start_progress("Извлечение аудио...")
        
        def extract():
            cmd = f'ffmpeg -y -i "{input_file}" -vn -acodec copy "{output_file}" -hide_banner'
            if self.run_command(cmd):
                self.log(f"✓ Аудио извлечено: {output_file.name}")
                self.refresh_files()
                self.stop_progress("Аудио извлечено")
            else:
                self.log("❌ Ошибка при извлечении аудио")
                self.stop_progress("Ошибка")
                
        threading.Thread(target=extract, daemon=True).start()
        
    def transcribe_audio(self):
        selected_file = self.get_selected_file()
        if not selected_file:
            return
            
        audio_file = self.audio_dir / selected_file
        if not audio_file.exists():
            messagebox.showerror("Ошибка", f"Файл не найден в папке audio: {selected_file}")
            return
            
        if audio_file.suffix.lower() not in {'.m4a', '.wav', '.mp3', '.ogg'}:
            messagebox.showerror("Ошибка", "Выберите аудиофайл")
            return
            
        self.log(f"Транскрибируем: {selected_file}")
        self.start_progress("Транскрипция аудио...", determinate=True)
        self.stop_event.clear()

        def transcribe():
            try:
                self.run_transcription(audio_file)
                txt_file = audio_file.with_suffix('.txt')
                transcript_file = self.transcripts_dir / txt_file.name
                if txt_file.exists():
                    txt_file.rename(transcript_file)
                    self.log(f"✓ Транскрипция готова: transcripts/{transcript_file.name}")
                else:
                    self.log(f"✓ Транскрипция готова: {audio_file.stem}.txt")
                self.refresh_files()
                self.stop_progress("Транскрипция завершена")
            except TranscriptionCancelled:
                self.log("⏹ Транскрипция остановлена пользователем")
                self.stop_progress("Остановлено")
            except Exception as e:
                self.log(f"❌ Ошибка при транскрипции: {e}")
                self.stop_progress("Ошибка")

        self.current_thread = threading.Thread(target=transcribe, daemon=True)
        self.current_thread.start()
        
    def full_cycle(self):
        selected_file = self.get_selected_file()
        if not selected_file:
            return
            
        input_file = self.input_dir / selected_file
        if not input_file.exists():
            messagebox.showerror("Ошибка", f"Файл не найден в папке input: {selected_file}")
            return
            
        if input_file.suffix.lower() not in {'.mp4', '.avi', '.mkv', '.mov'}:
            messagebox.showerror("Ошибка", "Выберите видеофайл для полного цикла")
            return
            
        audio_file = self.audio_dir / f"{input_file.stem}_audio.m4a"
        
        self.log(f"=== ПОЛНЫЙ ЦИКЛ для: {selected_file} ===")
        self.start_progress("Полный цикл обработки...")
        self.stop_event.clear()

        def full_process():
            self.log("Шаг 1: Извлечение аудио...")
            self.progress_var.set("Извлечение аудио...")
            cmd1 = f'ffmpeg -y -i "{input_file}" -vn -acodec copy "{audio_file}" -hide_banner'
            if not self.run_command(cmd1):
                self.log("❌ Ошибка при извлечении аудио")
                self.stop_progress("Ошибка")
                return

            if self.stop_event.is_set():
                self.stop_progress("Остановлено")
                return

            self.log("✓ Аудио извлечено")

            self.log("Шаг 2: Транскрипция...")
            self.start_progress("Транскрипция аудио...", determinate=True)
            try:
                self.run_transcription(audio_file)
            except TranscriptionCancelled:
                self.log("⏹ Транскрипция остановлена пользователем")
                self.stop_progress("Остановлено")
                return
            except Exception as e:
                self.log(f"❌ Ошибка при транскрипции: {e}")
                self.stop_progress("Ошибка")
                return

            txt_file = audio_file.with_suffix('.txt')
            transcript_file = self.transcripts_dir / txt_file.name
            if txt_file.exists():
                txt_file.rename(transcript_file)

            self.log("✓ Транскрипция готова")
            self.log("=== ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН ===")
            self.refresh_files()
            self.stop_progress("Полный цикл завершен")

        self.current_thread = threading.Thread(target=full_process, daemon=True)
        self.current_thread.start()


def transcribe_file(audio_path: Path, model_name: str = "large-v3", progress_callback=None, stop_event: threading.Event | None = None):
    """Transcribe the given audio file and save a `.txt` alongside it."""
    try:
        import whisper
        import tqdm
        import time
        from functools import partial

        start_time = time.time()

        class TqdmLogger(tqdm.tqdm):
            def __init__(self, *args, **kwargs):
                self._callback = kwargs.pop("progress_callback", None)
                self._stop_event = kwargs.pop("stop_event", None)
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                if self._stop_event and self._stop_event.is_set():
                    raise TranscriptionCancelled()
                super().update(n)
                if self._callback:
                    elapsed = time.time() - start_time
                    rate = self.n / elapsed if elapsed > 0 else 0
                    remaining = (self.total - self.n) / rate if self.total and rate > 0 else None
                    processed = int(self.n)
                    total_items = int(self.total) if self.total else 0
                    self._callback(processed, total_items, elapsed, remaining)

        old_tqdm = tqdm.tqdm
        tqdm.tqdm = partial(TqdmLogger, progress_callback=progress_callback, stop_event=stop_event)
        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(str(audio_path))
        finally:
            tqdm.tqdm = old_tqdm

        txt_path = audio_path.with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result.get('text', ''))
        print(f"✓ Транскрипция сохранена в {txt_path}")
    except TranscriptionCancelled:
        print("⏹ Транскрипция остановлена")
        raise
    except Exception as e:
        # Выводим ошибку, чтобы GUI мог отобразить её в логе
        print(f"❌ Ошибка транскрипции: {e}")
        raise


if __name__ == "__main__":
    # При наличии аргумента командной строки работаем в режиме CLI
    if len(sys.argv) > 1:
        audio = Path(sys.argv[1])
        transcribe_file(audio)
    else:
        try:
            root = tk.Tk()
            app = AudioProcessorGUI(root)
            root.mainloop()
        except Exception as e:
            import traceback
            with open("error_log.txt", "w", encoding="utf-8") as f:
                f.write(f"Ошибка при запуске GUI:\n{e}\n\n")
                f.write(traceback.format_exc())
            try:
                import tkinter.messagebox as mb
                mb.showerror("Ошибка", f"Не удалось запустить программу:\n{e}")
            except Exception:
                print(f"Критическая ошибка: {e}")
                print(traceback.format_exc())
