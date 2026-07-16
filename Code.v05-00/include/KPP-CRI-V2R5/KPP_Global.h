#ifndef KPP_GLOBAL_H_INCLUDED
#define KPP_GLOBAL_H_INCLUDED

#include "omp.h"
#include "KPP/KPP_Parameters.h"

/* Declaration of global variables                                  */

extern double C[NSPECALL];                         /* Concentration of all species */
extern double * VAR;
extern double * FIX;
extern double RCONST[NREACT];                   /* Rate constants (global) */
extern double TIME;                             /* Current integration time */
extern double SUN;                              /* Sunlight intensity between [0,1] */
extern double TEMP;                             /* Temperature */
extern double RTOLS;                            /* (scalar) Relative tolerance */
extern double TSTART;                           /* Integration start time */
extern double TEND;                             /* Integration end time */
extern double DT;                               /* Integration step */
extern double ATOL[NSPEC];                      /* Absolute tolerance */
extern double RTOL[NSPEC];                      /* Relative tolerance */
extern double STEPMIN;                          /* Lower bound for integration step */
extern double STEPMAX;                          /* Upper bound for integration step */
extern double CFACTOR;                          /* Conversion factor for concentration units */
extern int DDMTYPE;                             /* DDM sensitivity w.r.t.: 0=init.val., 1=params */
extern int LOOKAT[NLOOKAT];                     /* Indexes of species to look at */
extern int MONITOR[NMONITOR];                   /* Indexes of species to monitor */
extern const char * SPC_NAMES[NSPEC];           /* Names of chemical species (const char*) */
extern char * SMASS[NMASS];                     /* Names of atoms for mass balance */
extern const char * EQN_NAMES[NREACT];          /* Equation names (const char*) */
extern char * EQN_TAGS[NREACT];                 /* Equation tags */

/* INLINED global variable declarations                             */

extern double NOON_JRATES[NPHOTOL];             /* Noon-time photolysis rates */
extern double PHOTOL[NPHOTOL];                  /* Photolysis rates */
extern double HET[NSPEC][3];                    /* Heterogeneous reaction rates */
extern double SZA_CST[3];                       /* Constants to compute cosSZA */

/* The following variables need to be declared THREADPRIVATE
 * because they get written to within an OpenMP parallel loop */
#pragma omp threadprivate( C, VAR, FIX, RCONST, TIME, SUN, TEMP, RTOLS, TSTART, TEND, DT, ATOL, RTOL, STEPMIN, STEPMAX, CFACTOR, DDMTYPE, NOON_JRATES, PHOTOL, HET, SZA_CST )

#endif /* KPP_GLOBAL_H_INCLUDED */
