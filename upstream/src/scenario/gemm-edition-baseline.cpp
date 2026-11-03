#include "gemm-edition.h"
QString Gemm::edition() { return "baseline"; }
QString Gemm::editionTitle() { return QString::fromUtf8("原始无优化版"); }
QString Gemm::editionAlgorithm() { return "baseline-v1"; }
