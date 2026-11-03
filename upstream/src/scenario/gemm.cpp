#include "gemm.h"
#include "gemm-edition.h"
#include "nativesocket.h"
#include "engine.h"
#include "room.h"
#include "roomthread.h"
#include "serverplayer.h"
#include "standard.h"
#include "standard-equips.h"
#include "skill.h"
#include "settings.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QSaveFile>
#include <QTimer>
#include <QSet>
#include <stdexcept>
#ifdef Q_OS_WIN
#include <windows.h>
#include <psapi.h>
#endif

namespace Gemm {
static QMutex mutex;
static QWaitCondition wake;
static Spec current;
static QJsonObject report;
static bool paused = false, cancelled = false;
static int permits = 0, modeSpeed = 0;
static QJsonArray trace;
static qint64 engineNs = 0;
static int rescues = 0, draws = 0, damages = 0, flips = 0;
static const int ExpandedSupply = 800;
static const int ExpandedReserve = 131072;
static void registerExpandedDeck() {
    static bool registered = false;
    if (registered) return;
    Package *p = new Package("gemm_cards_large", Package::CardPack);
    for (int i=0;i<ExpandedSupply;++i) (new Slash(Card::Spade,7))->setParent(p);
    for (int i=0;i<ExpandedSupply+ExpandedReserve;++i) (new Jink(Card::Heart,2))->setParent(p);
    (new KylinBow(Card::Diamond,5))->setParent(p);
    Sanguosha->addPackage(p);
    registered = true;
}

static QJsonArray json(const Matrix &m) {
    QJsonArray out;
    foreach (const QVector<int> &row, m) {
        QJsonArray r; foreach (int v, row) r.append(v); out.append(r);
    }
    return out;
}
static bool matrix(const QJsonValue &v, Matrix &m) {
    if (!v.isArray() || v.toArray().isEmpty() || v.toArray().size() > 2) return false;
    int width = -1;
    foreach (const QJsonValue &row, v.toArray()) {
        if (!row.isArray() || row.toArray().isEmpty() || row.toArray().size() > 2) return false;
        if (width < 0) width = row.toArray().size();
        if (row.toArray().size() != width) return false;
        QVector<int> r;
        foreach (const QJsonValue &x, row.toArray()) {
            if (!x.isDouble() || x.toDouble() < 0 || x.toDouble() > 100 || x.toDouble() != int(x.toDouble())) return false;
            r.append(x.toInt());
        }
        m.append(r);
    }
    return true;
}
static Matrix transpose(const Matrix &m) {
    Matrix out(m.first().size(), QVector<int>(m.size()));
    for (int i=0;i<m.size();++i) for(int j=0;j<m.first().size();++j) out[j][i]=m[i][j];
    return out;
}
static QList<Task> compile(const Matrix &a, const Matrix &b, bool sparse) {
    QList<Task> tasks;
    for(int i=0;i<a.size();++i) for(int j=0;j<b.first().size();++j) for(int k=0;k<b.size();++k) {
        if (sparse && b[k][j]==0) continue;
        for(int repeat=0;repeat<a[i][k];++repeat) { Task t={i,j,k}; tasks.append(t); }
    }
    return tasks;
}
bool configure(const QJsonObject &obj, QString &error) {
    Spec s;
    if (!matrix(obj.value("A"),s.a) || !matrix(obj.value("B"),s.b) || s.a.first().size()!=s.b.size()) {
        error=QString::fromUtf8("矩阵维度须为 1–2、元素为 0–100 整数，且 A 的列数等于 B 的行数。"); return false;
    }
    s.algorithm=obj.value("algorithm").toString(editionAlgorithm());
    if ((obj.contains("algorithm") && !obj["algorithm"].isString()) || s.algorithm!=editionAlgorithm()) {
        error=QString("This %1 executable only supports %2").arg(edition(),editionAlgorithm()); return false;
    }
    if(obj.contains("speed") && (!obj["speed"].isDouble() || obj["speed"].toDouble()!=obj["speed"].toInt(-1))) {
        error="Speed must be 0, 1 or 2"; return false;
    }
    s.speed=obj.value("speed").toInt(0);
    if(s.speed<0 || s.speed>2) { error="Invalid speed"; return false; }
    s.fault=obj.value("fault").toString();
    if(!s.fault.isEmpty() && s.fault!="no-rescue" && s.fault!="empty-deck" && s.fault!="no-range") {
        error="Unknown fault injection"; return false;
    }
    s.left=s.a; s.right=s.b; s.transposed=false;
    s.tasks=compile(s.left,s.right,s.algorithm!="baseline-v1");
    if(s.algorithm=="transpose-v1.2") {
        QList<Task> alternative=compile(transpose(s.b),transpose(s.a),true);
        if(alternative.size()<s.tasks.size()) {
            s.left=transpose(s.b); s.right=transpose(s.a); s.tasks=alternative; s.transposed=true;
        }
    }
    // Every valid input, including zero matrices, uses the same fixed resource pool.
    // Register before creating either client/server RoomState; no input-dependent deck switch.
    registerExpandedDeck();
    QMutexLocker lock(&mutex);
    current=s; modeSpeed=s.speed; cancelled=false; paused=false; permits=0;
    report=QJsonObject(); trace=QJsonArray(); engineNs=0; rescues=draws=damages=flips=0;
    report["schemaVersion"]=1;
    report["resourceVersion"]="uniform-large-v1";
    report["attackCapacity"]=ExpandedSupply;
    report["rescueCapacity"]=ExpandedSupply;
    report["edition"]=edition();report["settingsPath"]=Config.fileName();
    report["upstream"]="e8768851bd8054db9fd1b63cd6f1feca813590d7";
    report["A"]=json(s.a); report["B"]=json(s.b); report["algorithm"]=s.algorithm;
    report["transposed"]=s.transposed; report["tasks"]=s.tasks.size(); report["completed"]=0;
    report["speed"]=s.speed; report["status"]="preparing";report["paused"]=false;
    report["C"]=json(Matrix(s.a.size(),QVector<int>(s.b.first().size(),0)));
    return true;
}
Spec spec() { QMutexLocker lock(&mutex); return current; }
QJsonObject snapshot() { QMutexLocker lock(&mutex); return report; }
void pause(bool p) { QMutexLocker lock(&mutex); paused=p; report["paused"]=p; wake.wakeAll(); }
void step() { QMutexLocker lock(&mutex); paused=true; report["paused"]=true; ++permits; wake.wakeAll(); }
void cancel() { QMutexLocker lock(&mutex); cancelled=true; wake.wakeAll(); }
void setSpeed(int n) { QMutexLocker lock(&mutex); modeSpeed=qBound(0,n,2); report["speed"]=modeSpeed; wake.wakeAll(); }
int speed() { QMutexLocker lock(&mutex); return modeSpeed; }
bool active() { return Config.GameMode=="gemm"; }
QString deckPackage() { return "gemm_cards_large"; }
static void check(bool ok,const char *msg) { if(!ok) throw std::runtime_error(msg); }

void registerPackages() {
    Sanguosha->addScenario(new GemmScenario);
}

void initialize(Room *room) {
    QElapsedTimer timer; timer.start();
    const Spec s=spec(); const QList<ServerPlayer *> ps=room->getPlayers();
    check(ps.size()==2+s.inner()*s.cols()+s.rows()*s.cols(),"Wrong player count");
    QList<int> ids=room->getDrawPile(); qSort(ids);
    QList<int> slashes, reds; int bow=-1;
    foreach(int id,ids) {
        const Card *c=Sanguosha->getCard(id);
        if(c->isKindOf("Slash")) slashes.append(id);
        else if(c->isKindOf("Jink")) reds.append(id);
        else if(c->isKindOf("KylinBow")) bow=id;
    }
    const int supply=ExpandedSupply;
    const int reserve=ExpandedReserve;
    check(slashes.size()==supply && reds.size()==supply+reserve && bow>=0,"Incomplete computation deck");
    check(s.tasks.size()<=supply,"Insufficient attack/rescue capacity");
    // Fixed deterministic reserve, independent of the numerical product.
    room->getDrawPile()=ids;
    room->setCurrent(ps[0]);
    for(int k=0;k<s.inner();++k) for(int j=0;j<s.cols();++j) {
        ServerPlayer *p=ps[2+k*s.cols()+j];
        room->setPlayerProperty(p,"maxhp",s.right[k][j]+1);
        room->setPlayerProperty(p,"hp",1);
        QString label=QString("B[%1,%2]=%3").arg(k+1).arg(j+1).arg(s.right[k][j]);
        if(s.transposed) label=QString("A[%1,%2]=%3").arg(j+1).arg(k+1).arg(s.right[k][j]);
        room->setPlayerProperty(p,"screenname",label);
    }
    const int offset=2+s.inner()*s.cols();
    for(int i=0;i<s.rows();++i) for(int j=0;j<s.cols();++j) {
        ServerPlayer *p=ps[offset+i*s.cols()+j];
        int oi=s.transposed?j:i, oj=s.transposed?i:j;
        room->setPlayerProperty(p,"screenname",QString("C[%1,%2]").arg(oi+1).arg(oj+1));
    }
    room->setPlayerProperty(ps[0],"screenname",QString::fromUtf8("张飞 · 执行"));
    room->setPlayerProperty(ps[1],"screenname",QString::fromUtf8("华佗 · 急救"));
    DummyCard attack(slashes.mid(0,s.tasks.size()));
    if(!attack.getSubcards().isEmpty()) room->obtainCard(ps[0],&attack,false);
    DummyCard rescueSupply(reds.mid(0,s.fault=="no-rescue"?0:supply));
    if(!rescueSupply.getSubcards().isEmpty()) room->obtainCard(ps[1],&rescueSupply,false);
    if(s.fault!="no-range") room->moveCardTo(Sanguosha->getCard(bow),ps[0],Player::PlaceEquip);
    // Only the reserve is drawable; unused initial resources stay out of play.
    room->getDrawPile()=reds.mid(supply,s.fault=="empty-deck"?0:reserve);
    room->doBroadcastNotify(QSanProtocol::S_COMMAND_UPDATE_PILE,room->getDrawPile().size());
    QJsonArray initial;
    foreach(ServerPlayer *p,ps) {
        QJsonObject o; o["id"]=p->objectName(); o["general"]=p->getGeneralName(); o["label"]=p->screenName();
        o["hp"]=p->getHp();o["maxhp"]=p->getMaxHp();
        QJsonArray hand; foreach(const Card *c,p->getHandcards()) hand.append(c->getEffectiveId());
        o["hand"]=hand; initial.append(o);
    }
    QMutexLocker lock(&mutex); report["initialPlayers"]=initial; report["prepareMs"]=timer.nsecsElapsed()/1e6;
    report["drawPileCapacity"]=room->getDrawPile().size();
    QJsonArray pile;foreach(int id,room->getDrawPile())pile.append(id);report["initialDrawPile"]=pile;
    report["initialWeaponId"]=bow;
}

void observe(TriggerEvent event,ServerPlayer *player,const QVariant &data) {
    if(event==PreHpRecover) { ++rescues; }
    if(event==Damaged) { damages+=data.value<DamageStruct>().damage; }
    if(event==TurnedOver) ++flips;
    if(event==CardsMoveOneTime) {
        CardsMoveOneTimeStruct m=data.value<CardsMoveOneTimeStruct>();
        Q_UNUSED(m); // Draw count is observed once at each completed card-resolution boundary.
    }
    Q_UNUSED(player);
}
static Matrix readResult(Room *room,const Spec &s) {
    Matrix c(s.a.size(),QVector<int>(s.b.first().size(),0));
    const QList<ServerPlayer *> ps=room->getPlayers(); int off=2+s.inner()*s.cols();
    for(int i=0;i<s.rows();++i) for(int j=0;j<s.cols();++j)
        c[s.transposed?j:i][s.transposed?i:j]=ps[off+i*s.cols()+j]->getHandcardNum();
    return c;
}
void run(Room *room) {
    const Spec s=spec(); QElapsedTimer wall; wall.start();
    try {
        initialize(room);
        wall.restart();
        const QList<ServerPlayer *> ps=room->getPlayers();
        ServerPlayer *attacker=ps[0];
        room->getRoomState()->setCurrentCardUseReason(CardUseStruct::CARD_USE_REASON_PLAY);
        attacker->setPhase(Player::Play); room->broadcastProperty(attacker,"phase");
        { QMutexLocker lock(&mutex); report["status"]="running"; }
        for(int x=0;x<s.tasks.size();++x) {
            {
                QMutexLocker lock(&mutex);
                while(paused && permits==0 && !cancelled) wake.wait(&mutex);
                if(cancelled) throw std::runtime_error("Cancelled");
                if(permits>0) --permits;
            }
            room->getRoomState()->setCurrentCardUseReason(CardUseStruct::CARD_USE_REASON_PLAY);
            const Task t=s.tasks[x];
            ServerPlayer *caopi=ps[2+t.k*s.cols()+t.j];
            ServerPlayer *out=ps[2+s.inner()*s.cols()+t.i*s.cols()+t.j];
            room->setTag("GemmOutput",QVariant::fromValue(out));
            check(caopi->isAlive() && caopi->getHp()==1,"Caopi invariant violated");
            check(ps[1]->getHandcardNum()>0,"No rescue card available");
            check(room->getDrawPile().size()>=caopi->getMaxHp()-1,"Draw pile exhausted");
            const Card *slash=NULL;
            foreach(const Card *c,attacker->getHandcards()) if(c->isKindOf("Slash")) { slash=c; break; }
            check(slash && slash->isAvailable(attacker),"No legal Slash available");
            check(attacker->canSlash(caopi,slash,true),"Slash target out of range or prohibited");
            int before=out->getHandcardNum();
            QSet<int> previousHand=out->handCards().toSet();
            QList<int> rescueHand=ps[1]->handCards();
            LogMessage log; log.type="#GemmStep"; log.from=attacker; log.to<<caopi<<out;
            log.arg=QString::number(x+1); log.arg2=QString::number(s.tasks.size()); room->sendLog(log);
            QElapsedTimer cpu; cpu.start();
            // No direct damage/recovery/draw calls: this is an actual card use.
            room->useCard(CardUseStruct(slash,attacker,caopi),true);
            engineNs+=cpu.nsecsElapsed();
            check(caopi->isAlive() && caopi->getHp()==1,"Rescue did not restore Caopi");
            check(out->getHandcardNum()-before==s.right[t.k][t.j],"Fangzhu result mismatch");
            draws += out->getHandcardNum()-before;
            QJsonObject event; event["step"]=x+1; event["i"]=t.i;event["j"]=t.j;event["k"]=t.k;
            event["slashId"]=slash->getEffectiveId();event["target"]=caopi->objectName();event["output"]=out->objectName();
            event["before"]=before;event["after"]=out->getHandcardNum();event["caopiHp"]=caopi->getHp();
            QJsonArray drawn;foreach(int id,out->handCards()) if(!previousHand.contains(id)) drawn.append(id);
            QJsonArray rescued;foreach(int id,rescueHand) if(!ps[1]->handCards().contains(id)) rescued.append(id);
            event["drawnCardIds"]=drawn;event["rescueCardIds"]=rescued;
            event["originalI"]=s.transposed?t.j:t.i;event["originalJ"]=s.transposed?t.i:t.j;
            {
                QMutexLocker lock(&mutex);trace.append(event);report["completed"]=x+1;report["C"]=json(readResult(room,s));
                report["engineMs"]=engineNs/1e6;report["rescues"]=rescues;report["damagePoints"]=damages;
                report["fangzhu"]=flips;report["drawnCards"]=draws;report["current"]=event;
                if(modeSpeed<2 && !cancelled) wake.wait(&mutex,modeSpeed==0?900:90);
            }
        }
        QMutexLocker lock(&mutex);report["C"]=json(readResult(room,s));report["status"]="complete";
    } catch(const std::exception &e) {
        QMutexLocker lock(&mutex);report["status"]="failed";report["error"]=QString::fromUtf8(e.what());
    } catch(TriggerEvent) {
        QMutexLocker lock(&mutex);report["status"]="failed";report["error"]="Unexpected game termination";
    }
    QMutexLocker lock(&mutex);
    report["engineMs"]=engineNs/1e6;report["runWallMs"]=wall.nsecsElapsed()/1e6;
    report["rescues"]=rescues;report["damagePoints"]=damages;report["fangzhu"]=flips;report["drawnCards"]=draws;
    report["judgements"]=0;report["trace"]=trace;
    report["activeCardUses"]=trace.size();report["consumedCards"]=trace.size()+rescues;
    QJsonArray finalPlayers;foreach(ServerPlayer *p,room->getPlayers()) {
        QJsonObject o;o["id"]=p->objectName();o["hp"]=p->getHp();o["handCount"]=p->getHandcardNum();o["faceUp"]=p->faceUp();finalPlayers.append(o);
    }
    report["finalPlayers"]=finalPlayers;
#ifdef Q_OS_WIN
    FILETIME created,exited,kernel,user;
    if(GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user)) {
        ULARGE_INTEGER k,u;k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;
        u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;
        report["processCpuMs"]=double(k.QuadPart+u.QuadPart)/10000.0;
    }
    HMODULE psapi=LoadLibraryW(L"psapi.dll");
    if(psapi) {
        typedef BOOL (WINAPI *MemoryInfo)(HANDLE,PROCESS_MEMORY_COUNTERS *,DWORD);
        MemoryInfo getMemory=reinterpret_cast<MemoryInfo>(GetProcAddress(psapi,"GetProcessMemoryInfo"));
        PROCESS_MEMORY_COUNTERS memory;memset(&memory,0,sizeof(memory));memory.cb=sizeof(memory);
        if(getMemory && getMemory(GetCurrentProcess(),&memory,sizeof(memory))) {
            report["peakWorkingSetBytes"]=double(memory.PeakWorkingSetSize);
            report["workingSetBytes"]=double(memory.WorkingSetSize);
        }
        FreeLibrary(psapi);
    }
#endif
    report["resourceNote"]="CPU time and working set cover the whole process including startup; GPU usage is not measured";
    report["timingNote"]="engineMs: card-resolution wall time without intentional delays; runWallMs includes playback pacing and pauses, not GPU completion";
}
int commandLine(const QString &input,const QString &output) {
    QFile f(input);QString error;
    const auto reject=[output](const QString &message) {
        QJsonObject r;r["status"]="invalid-input";r["error"]=message;
        QSaveFile f(output);if(!f.open(QIODevice::WriteOnly)) return 3;
        f.write(QJsonDocument(r).toJson());return f.commit()?2:3;
    };
    if(!f.open(QIODevice::ReadOnly)) return reject(f.errorString());
    QJsonParseError parseError;QJsonDocument document=QJsonDocument::fromJson(f.readAll(),&parseError);
    if(parseError.error!=QJsonParseError::NoError) return reject(parseError.errorString());
    if(!document.isObject()) return reject("Input must be a JSON object");
    const QJsonObject inputObject=document.object();
    if(!configure(inputObject,error)) return reject(error);
    const bool testControls=inputObject.value("testControls").toBool();
    if(testControls) pause(true);
    Config.GameMode="02p";
    foreach(int id,Sanguosha->getRandomCards()) if(Sanguosha->getEngineCard(id)->getPackage().startsWith("gemm_cards")) return 4;
    Config.GameMode="gemm";Config.RandomSeat=false;Config.Enable2ndGeneral=false;Config.EnableBasara=false;
    Config.EnableHegemony=false;Config.OriginAIDelay=0;Config.AIDelay=0;Config.CountDownSeconds=0;
    if(inputObject.value("testListener").toBool()) {
        NativeServerSocket *listener=new NativeServerSocket;
        listener->setParent(qApp);
        if(!listener->listen()) return reject("Local listener failed");
        QMutexLocker lock(&mutex);report["serverPort"]=int(Config.ServerPort);
    }
    Room *room=new Room(qApp,"gemm");room->setProperty("to_test","gemm");
    QTimer poll;int controlStage=0,controlTicks=0;bool controlPassed=false;
    QObject::connect(&poll,&QTimer::timeout,[room,output,testControls,&controlStage,&controlTicks,&controlPassed]() {
        if(testControls) {
            QJsonObject v=snapshot();int n=v["completed"].toInt();
            if(v["status"].toString()=="running") {
                if(controlStage==0 && ++controlTicks>=10) {
                    if(n!=0) {cancel();return;}
                    step();controlStage=1;controlTicks=0;
                } else if(controlStage==1 && n==1 && ++controlTicks>=10) {
                    step();controlStage=2;controlTicks=0;
                } else if(controlStage==2 && n==2 && ++controlTicks>=10) {
                    controlPassed=true;pause(false);controlStage=3;
                }
            }
        }
        if(!room->getThread() || room->getThread()->isRunning()) return;
        QJsonObject r=snapshot();QString state=r.value("status").toString();
        if(state!="complete" && state!="failed") return;
        if(testControls) r["controlTestPassed"]=controlPassed;
        QSaveFile f(output);if(!f.open(QIODevice::WriteOnly)) {qApp->exit(3);return;}
        f.write(QJsonDocument(r).toJson());if(!f.commit()) {qApp->exit(3);return;}
        qApp->exit(state=="complete"?0:1);
    });
    poll.start(10);room->addRobotCommand(NULL,-1);
    return qApp->exec();
}
}

class GemmRule : public ScenarioRule {
public:
    GemmRule(Scenario *s):ScenarioRule(s) { events<<GameStart<<PreHpRecover<<Damaged<<TurnedOver<<CardsMoveOneTime; }
    int getPriority(TriggerEvent) const {return 10;}
    bool trigger(TriggerEvent event,Room *room,ServerPlayer *player,QVariant &data) const {
        if(event==GameStart) return true; // Initialization is inside run()'s failure boundary.
        Gemm::observe(event,player,data);return false;
    }
};
GemmScenario::GemmScenario():Scenario("gemm") {rule=new GemmRule(this);}
int GemmScenario::getPlayerCount() const {Gemm::Spec s=Gemm::spec();return s.left.isEmpty()?10:2+s.inner()*s.cols()+s.rows()*s.cols();}
QString GemmScenario::getRoles() const {return "Z"+QString(getPlayerCount()-1,'F');}
void GemmScenario::assign(QStringList &generals,QStringList &roles) const {
    Gemm::Spec s=Gemm::spec();generals<<"zhangfei"<<"huatuo";
    for(int k=0;k<s.inner()*s.cols();++k) generals<<"caopi";
    QStringList outputs;outputs<<"guanyu"<<"zhaoyun"<<"machao"<<"huangzhong";
    for(int i=0;i<s.rows()*s.cols();++i) generals<<outputs[i];
    roles<<"lord";for(int i=1;i<generals.size();++i) roles<<"rebel";
}
const Card *GemmAI::askForSinglePeach(ServerPlayer *) {
    if(self->getGeneralName()!="huatuo") return NULL;
    const ViewAsSkill *skill=Sanguosha->getViewAsSkill("jijiu");
    if(!skill || !skill->isEnabledAtResponse(self,"peach")) return NULL;
    foreach(const Card *c,self->getHandcards()) if(c->isRed()) {
        QList<const Card *> cards;cards<<c;
        return skill->viewAs(cards);
    }
    return NULL;
}
ServerPlayer *GemmAI::askForPlayerChosen(const QList<ServerPlayer *> &targets,const QString &reason) {
    if(reason=="fangzhu") {
        ServerPlayer *p=room->getTag("GemmOutput").value<ServerPlayer *>();
        return targets.contains(p)?p:NULL;
    }
    return NULL;
}
