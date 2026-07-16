#include "KPP/KPP_Global.h"
#include "KPP/KPP_Parameters.h"

/* Definition of global variables */
double C[NSPEC];
double * VAR = &C[0];
double * FIX = &C[NVAR];
double RCONST[NREACT];
double TIME;
int LOOKAT[NLOOKAT];
const char * SPC_NAMES[NSPEC] = {
    "NO", "NO2", "O3", "CO", "CH4", "SO2", "HNO3", "H2O", 
    /* This list is incomplete and just a placeholder to satisfy the linker if needed.
       The actual names are usually in KPP_Monitor.cpp */
    "TEMP"
};
char * SMASS[NMASS];
const char * EQN_NAMES[NREACT];
char * EQN_TAGS[NREACT];

double NOON_JRATES[NPHOTOL];
double PHOTOL[NPHOTOL];
double HET[NSPEC][3];
double SZA_CST[3];
