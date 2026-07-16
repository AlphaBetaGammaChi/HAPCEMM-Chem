#include "KPP/KPP_Global.h"
#include "KPP/KPP_Parameters.h"

/* Definition of global chemistry variables for CRI-v2r5 */
double C[NSPECALL];
double * VAR = &C[0];
double * FIX = &C[NVAR];
double RCONST[NREACT];
double TIME;
int LOOKAT[1];
int MONITOR[1];
const char * SPC_NAMES[NSPEC];
const char * EQN_NAMES[NREACT];
char * EQN_TAGS[NREACT];

double NOON_JRATES[NPHOTOL];
double PHOTOL[NPHOTOL];
double HET[NSPEC][3];
double SZA_CST[3];

/* Additional solver variables defined in KPP_Global.h */
double SUN;
double TEMP;
double RTOLS;
double TSTART;
double TEND;
double DT;
double ATOL[NVAR];
double RTOL[NVAR];
double STEPMIN;
double STEPMAX;
double CFACTOR;
int DDMTYPE;
