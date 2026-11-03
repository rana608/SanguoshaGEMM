#ifndef GEMM_EDITION_H
#define GEMM_EDITION_H
#include <QString>
namespace Gemm {
// These functions are linked from exactly one edition object, never from user settings.
QString edition();
QString editionTitle();
QString editionAlgorithm();
}
#endif
