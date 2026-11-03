#include <QtWidgets>
#include <QJsonDocument>
#include <QJsonArray>
#include <QSaveFile>
#include <windows.h>

// The two clients remain unmodified, detached programs with separate working directories.
struct Edition {
    QString name, label, description, program;
    QPushButton *button;
    QLabel *status;
    HANDLE process = NULL;
    qint64 pid = 0;
};

class Launcher : public QWidget {
public:
    QList<Edition *> editions;
    QPixmap backdrop;
    QString root;

    Launcher(const QString &directory) : root(directory) {
        setWindowTitle(QString::fromUtf8("三国杀 GEMM · 矩阵演武"));
        setMinimumSize(760, 480);resize(880, 550);
        setWindowIcon(QIcon(QDir(QCoreApplication::applicationDirPath()).filePath("assets/sgs.ico")));
        backdrop.load(QDir(QCoreApplication::applicationDirPath()).filePath("assets/backdrop.jpg"));
        setFont(QFont("Microsoft YaHei", 10));
        setStyleSheet(
            "QLabel { color:#f0e4c8; background:transparent; }"
            "QLabel#subtitle { color:#c0c8b7; font-size:14px; }"
            "QLabel#title { font-family:KaiTi; font-size:46px; color:#e0bf7c; }"
            "QLabel#edition { font-size:23px; color:#f0e4c8; }"
            "QLabel#status { font-size:12px; color:#d3c4a3; }"
            "QPushButton { background:#29372e; color:#f0e4c8; border:1px solid #b8995c;"
            " padding:15px 25px; font-size:17px; border-radius:3px; }"
            "QPushButton:hover { background:#3c4c3b; border-color:#e0bf7c; }"
            "QPushButton:pressed { background:#17231c; }"
            "QPushButton:focus { border:2px solid #f0d28c; padding:14px 24px; }"
            "QPushButton:disabled { color:#9ca693; border-color:#64715e; background:#263229; }");
        QVBoxLayout *layout = new QVBoxLayout(this);layout->setContentsMargins(48,32,48,26);layout->setSpacing(12);
        QLabel *brand = new QLabel(QString::fromUtf8("三国杀 GEMM"));brand->setObjectName("subtitle");layout->addWidget(brand,0,Qt::AlignHCenter);
        QLabel *title = new QLabel(QString::fromUtf8("矩 阵 演 武"));title->setObjectName("title");layout->addWidget(title,0,Qt::AlignHCenter);
        QLabel *intro = new QLabel(QString::fromUtf8("张飞出杀 · 华佗急救 · 曹丕放逐"));intro->setObjectName("subtitle");layout->addWidget(intro,0,Qt::AlignHCenter);
        layout->addStretch(1);
        QHBoxLayout *choices = new QHBoxLayout;choices->setSpacing(42);
        addEdition(choices,"Baseline",QString::fromUtf8("原始版本"),QString::fromUtf8("按顺序完整结算"),QString::fromUtf8("启动原始版"));
        QFrame *divider=new QFrame;divider->setFixedWidth(1);divider->setStyleSheet("background:#75633e;");choices->addWidget(divider);
        addEdition(choices,"Optimized",QString::fromUtf8("优化版本"),QString::fromUtf8("跳过零项 · 自动选择计算方向"),QString::fromUtf8("启动优化版"));
        layout->addLayout(choices);layout->addStretch(1);
        QLabel *hint = new QLabel(QString::fromUtf8("启动后输入矩阵，选择正常、加速或极速，进入牌桌观看。"));hint->setObjectName("subtitle");hint->setWordWrap(true);hint->setAlignment(Qt::AlignCenter);layout->addWidget(hint);
        QLabel *scope = new QLabel(QString::fromUtf8("矩阵行列 1–2 · 元素 0–100 · 两个版本可同时运行"));scope->setObjectName("status");layout->addWidget(scope,0,Qt::AlignHCenter);
        QTimer *timer=new QTimer(this);
        connect(timer,&QTimer::timeout,[this](){refresh();});timer->start(1000);
        refresh();
    }
    ~Launcher() {
        foreach(Edition *e,editions) { if(e->process) CloseHandle(e->process);delete e; }
    }
    QString resolve(const QString &name) const {
        const QString relative="SanguoshaGEMM-"+name+"/SanguoshaGEMM-"+name+".exe";
        // Unified ZIP: children of the launcher. Workspace: sibling edition folders.
        QString path=QDir(root).absoluteFilePath(relative);
        if(QFileInfo(path).isFile()) return QDir::cleanPath(path);
        path=QDir(root).absoluteFilePath("../"+relative);
        return QDir::cleanPath(path);
    }
    void addEdition(QHBoxLayout *layout,const QString &name,const QString &label,const QString &description,const QString &buttonText) {
        Edition *e=new Edition;e->name=name;e->label=label;e->description=description;
        QVBoxLayout *column=new QVBoxLayout;column->setSpacing(15);
        QLabel *heading=new QLabel(label);heading->setObjectName("edition");column->addWidget(heading,0,Qt::AlignHCenter);
        QLabel *detail=new QLabel(description);detail->setObjectName("subtitle");detail->setAlignment(Qt::AlignCenter);column->addWidget(detail);
        e->button=new QPushButton(buttonText);e->button->setObjectName(name.toLower()+"Button");e->button->setMinimumHeight(58);
        column->addWidget(e->button);e->status=new QLabel;e->status->setObjectName("status");e->status->setWordWrap(true);e->status->setAlignment(Qt::AlignCenter);e->status->setMinimumHeight(38);column->addWidget(e->status);
        layout->addLayout(column,1);editions.append(e);
        connect(e->button,&QPushButton::clicked,[this,e](){launch(e);});
    }
    bool running(Edition *e) const { return e->process && WaitForSingleObject(e->process,0)==WAIT_TIMEOUT; }
    void refresh() {
        foreach(Edition *e,editions) {
            if(running(e)) {e->button->setEnabled(false);continue;}
            if(e->process) {CloseHandle(e->process);e->process=NULL;e->status->setText(QString::fromUtf8("客户端已关闭，可再次启动。"));}
            e->program=resolve(e->name);
            bool exists=QFileInfo(e->program).isFile();e->button->setEnabled(exists);
            if(!exists) e->status->setText(QString::fromUtf8("未找到此版本，请完整解压统一启动包。"));
            else if(e->status->text().startsWith(QString::fromUtf8("未找到"))) e->status->clear();
        }
    }
    void launch(Edition *e) {
        if(running(e)) return;
        e->program=resolve(e->name);
        if(!QFileInfo(e->program).isFile()) {refresh();return;}
        qint64 pid=0;
        if(!QProcess::startDetached(e->program,QStringList()<<"--gemm",QFileInfo(e->program).absolutePath(),&pid)) {
            e->status->setText(QString::fromUtf8("启动失败，请检查是否已完整解压程序。"));return;
        }
        e->pid=pid;e->process=OpenProcess(SYNCHRONIZE,FALSE,DWORD(pid));
        e->status->setText(QString::fromUtf8("已启动，请在客户端输入矩阵。"));e->button->setEnabled(false);
    }
    QJsonObject state() const {
        QJsonArray array;
        foreach(Edition *e,editions) {
            QJsonObject o;o["edition"]=e->name;o["button"]=e->button->text();o["enabled"]=e->button->isEnabled();
            o["program"]=e->program;o["workingDirectory"]=QFileInfo(e->program).absolutePath();
            o["arguments"]=QJsonArray()<<"--gemm";o["pid"]=double(e->pid);o["running"]=running(e);o["status"]=e->status->text();array.append(o);
        }
        QJsonObject result;result["editions"]=array;return result;
    }
protected:
    void paintEvent(QPaintEvent *) {
        QPainter p(this);p.fillRect(rect(),QColor("#18251f"));
        if(!backdrop.isNull()) {
            QPixmap scaled=backdrop.scaled(size(),Qt::KeepAspectRatioByExpanding,Qt::SmoothTransformation);
            p.drawPixmap((width()-scaled.width())/2,(height()-scaled.height())/2,scaled);
            p.fillRect(rect(),QColor(12,24,18,192));
        }
        p.setPen(QColor("#75633e"));p.drawRect(rect().adjusted(12,12,-13,-13));
    }
};

static bool save(const QString &path,const QJsonObject &o) {
    QSaveFile f(path);if(!f.open(QIODevice::WriteOnly)) return false;
    f.write(QJsonDocument(o).toJson());return f.commit();
}

int main(int argc,char **argv) {
    bool test=false;
    for(int i=1;i<argc;++i) if(QByteArray(argv[i])=="--self-test" || QByteArray(argv[i])=="--render" || QByteArray(argv[i])=="--check") test=true;
    if(test) qputenv("QT_QPA_PLATFORM","offscreen");
    QApplication app(argc,argv);app.setQuitOnLastWindowClosed(true);
    // Qt 5.5's offscreen plugin does not discover Windows fonts automatically.
    // Read installed fonts for the same typography; do not redistribute system fonts.
    if(test) {
        QDir fonts(QString::fromLocal8Bit(qgetenv("WINDIR"))+"/Fonts");
        foreach(const QString &name,QStringList()<<"msyh.ttc"<<"simkai.ttf"<<"segoeui.ttf")
            if(QFileInfo(fonts.filePath(name)).isFile()) QFontDatabase::addApplicationFont(fonts.filePath(name));
    }
    QStringList args=app.arguments();QString root=app.applicationDirPath();
    if(args.size()==4 && args[1]=="--check") root=QFileInfo(args[2]).absoluteFilePath();
    Launcher window(root);
    if(args.size()==4 && args[1]=="--check") return save(args[3],window.state())?0:2;
    window.show();
    if(args.size()==3 && args[1]=="--render") {
        QTimer::singleShot(150,[&](){app.exit(window.grab().save(args[2])?0:2);});
    } else if(args.size()==3 && args[1]=="--self-test") {
        // Background application test: exercise both real button handlers. Children
        // inherit offscreen mode, so no desktop is read or operated.
        foreach(Edition *e,window.editions) e->button->click();
        QTimer::singleShot(2500,[&](){
            bool ok=true;foreach(Edition *e,window.editions) ok=ok && window.running(e) && !e->button->isEnabled();
            QJsonObject r=window.state();r["passed"]=ok;
            foreach(Edition *e,window.editions) if(e->pid) {
                HANDLE owned=OpenProcess(PROCESS_TERMINATE|SYNCHRONIZE,FALSE,DWORD(e->pid));
                if(owned) {TerminateProcess(owned,0);WaitForSingleObject(owned,3000);CloseHandle(owned);}
            }
            window.refresh();bool reset=true;foreach(Edition *e,window.editions) reset=reset && e->button->isEnabled();
            r["buttonsResetAfterExit"]=reset;app.exit(save(args[2],r) && ok && reset?0:2);
        });
    }
    return app.exec();
}
