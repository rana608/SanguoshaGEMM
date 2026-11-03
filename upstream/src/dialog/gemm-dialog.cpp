#include "gemm-dialog.h"
#include "gemm.h"
#include "gemm-edition.h"
#include <QtWidgets>
#include <QJsonDocument>
#include <QJsonArray>

static QJsonArray parseMatrix(const QString &s) {
    QJsonArray matrix;
    foreach(QString row,s.trimmed().split(QRegExp("[;\\n]+"),QString::SkipEmptyParts)) {
        QJsonArray cells;
        foreach(QString cell,row.trimmed().split(QRegExp("[,，\\s]+"),QString::SkipEmptyParts)) {
            bool ok=false; double n=cell.toDouble(&ok);cells.append(ok?QJsonValue(n):QJsonValue());
        }
        matrix.append(cells);
    }
    return matrix;
}
static QString matrixText(const QJsonValue &v) {
    QStringList lines;
    foreach(QJsonValue row,v.toArray()) {
        QStringList cells;foreach(QJsonValue x,row.toArray()) cells<<QString::number(x.toInt());
        lines<<cells.join(" ");
    }
    return lines.join("\n");
}
GemmDialog::GemmDialog(QWidget *parent):QDialog(parent) {
    setWindowTitle(QString::fromUtf8("矩阵演武 · ")+Gemm::editionTitle());resize(640,430);
    QVBoxLayout *layout=new QVBoxLayout(this);
    QLabel *intro=new QLabel(QString::fromUtf8("张飞出杀，华佗急救，曹丕放逐。<br>结果武将的手牌数，就是矩阵的答案。"));
    layout->addWidget(intro);
    QHBoxLayout *matrices=new QHBoxLayout;
    a=new QPlainTextEdit("1 2\n3 0");b=new QPlainTextEdit("2 1\n1 2");
    foreach(QPlainTextEdit *edit,QList<QPlainTextEdit *>()<<a<<b) {
        QVBoxLayout *column=new QVBoxLayout;column->addWidget(new QLabel(edit==a?"A":"B"));
        edit->setMaximumHeight(110);column->addWidget(edit);matrices->addLayout(column);
    }
    layout->addLayout(matrices);
    layout->addWidget(new QLabel(QString::fromUtf8("每行一行数据，数字用空格分隔。维度 1–2，整数 0–100。\n所有输入统一使用大牌堆；大数值建议极速运行。")));
    algorithm=new QComboBox;algorithm->addItem(Gemm::editionTitle(),Gemm::editionAlgorithm());
    algorithm->setEnabled(false);
    speed=new QComboBox;speed->addItems(QStringList()<<QString::fromUtf8("正常演示")<<QString::fromUtf8("加速演示")<<QString::fromUtf8("极速结算 · 跳过动画"));
    QFormLayout *form=new QFormLayout;form->addRow(QString::fromUtf8("算法"),algorithm);form->addRow(QString::fromUtf8("播放"),speed);layout->addLayout(form);
    error=new QLabel;error->setWordWrap(true);layout->addWidget(error);
    QHBoxLayout *actions=new QHBoxLayout;
    QPushButton *example=new QPushButton(QString::fromUtf8("优化对比样例"));
    connect(example,&QPushButton::clicked,[this](){a->setPlainText("9 8\n7 6");b->setPlainText("1 0\n0 1");});
    QPushButton *loadButton=new QPushButton(QString::fromUtf8("载入记录"));connect(loadButton,SIGNAL(clicked()),this,SLOT(load()));
    QPushButton *go=new QPushButton(QString::fromUtf8("进入牌桌"));go->setDefault(true);connect(go,SIGNAL(clicked()),this,SLOT(validate()));
    actions->addWidget(example);actions->addWidget(loadButton);actions->addStretch();actions->addWidget(go);layout->addLayout(actions);
}
QJsonObject GemmDialog::input() const {
    QJsonObject o;o["A"]=parseMatrix(a->toPlainText());o["B"]=parseMatrix(b->toPlainText());
    o["algorithm"]=algorithm->currentData().toString();o["speed"]=speed->currentIndex();return o;
}
void GemmDialog::validate() {
    QString message;if(!Gemm::configure(input(),message)) {error->setText(message);return;}accept();
}
void GemmDialog::load() {
    QString path=QFileDialog::getOpenFileName(this,QString::fromUtf8("载入计算记录"),QString(),"JSON (*.json)");
    if(path.isEmpty())return;QFile file(path);if(!file.open(QIODevice::ReadOnly)) {error->setText(file.errorString());return;}
    QJsonParseError pe;QJsonObject o=QJsonDocument::fromJson(file.readAll(),&pe).object();
    if(pe.error!=QJsonParseError::NoError) {error->setText(pe.errorString());return;}
    QString message;if(!Gemm::configure(o,message)) {error->setText(message);return;}
    a->setPlainText(matrixText(o["A"]));b->setPlainText(matrixText(o["B"]));
    int i=algorithm->findData(o["algorithm"].toString());algorithm->setCurrentIndex(qMax(0,i));
    speed->setCurrentIndex(qBound(0,o["speed"].toInt(),2));
}
