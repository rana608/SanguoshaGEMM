#ifndef GEMM_DIALOG_H
#define GEMM_DIALOG_H
#include <QDialog>
#include <QJsonObject>
class QPlainTextEdit;
class QComboBox;
class QLabel;
class GemmDialog : public QDialog {
    Q_OBJECT
public:
    GemmDialog(QWidget *parent=0);
    QJsonObject input() const;
private:
    QPlainTextEdit *a,*b;
    QComboBox *algorithm,*speed;
    QLabel *error;
private slots:
    void validate();
    void load();
};
#endif
