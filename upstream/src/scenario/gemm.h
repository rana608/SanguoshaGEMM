#ifndef GEMM_H
#define GEMM_H
#include "scenario.h"
#include "ai.h"
#include <QJsonObject>
#include <QMutex>
#include <QWaitCondition>
#include <QElapsedTimer>

namespace Gemm {
typedef QVector<QVector<int> > Matrix;
struct Task { int i, j, k; };
struct Spec {
    Matrix a, b, left, right;
    QList<Task> tasks;
    QString algorithm, fault;
    bool transposed;
    int speed;
    int rows() const { return left.size(); }
    int inner() const { return right.size(); }
    int cols() const { return right.first().size(); }
};
bool configure(const QJsonObject &, QString &error);
Spec spec();
QJsonObject snapshot();
void pause(bool);
void step();
void cancel();
void setSpeed(int);
int speed();
bool active();
QString deckPackage();
void run(Room *);
void initialize(Room *);
void observe(TriggerEvent, ServerPlayer *, const QVariant &);
void registerPackages();
int commandLine(const QString &input, const QString &output);
}

class GemmScenario : public Scenario {
    Q_OBJECT
public:
    GemmScenario();
    int getPlayerCount() const;
    QString getRoles() const;
    void assign(QStringList &, QStringList &) const;
    void onTagSet(Room *, const QString &) const {}
};

class GemmAI : public TrustAI {
public:
    GemmAI(ServerPlayer *p) : TrustAI(p) {}
    bool askForSkillInvoke(const QString &, const QVariant &) { return false; }
    const Card *askForCard(const QString &, const QString &, const QVariant &) { return NULL; }
    const Card *askForSinglePeach(ServerPlayer *);
    ServerPlayer *askForPlayerChosen(const QList<ServerPlayer *> &, const QString &);
};
#endif
