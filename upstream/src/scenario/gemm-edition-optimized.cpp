#include "gemm-edition.h"
QString Gemm::edition() { return "optimized"; }
QString Gemm::editionTitle() { return QString::fromUtf8("优化版"); }
QString Gemm::editionAlgorithm() { return "transpose-v1.2"; }
