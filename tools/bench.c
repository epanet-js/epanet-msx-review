/* Benchmark driver for EPANET-MSX: times one network and reaction file in one
 * way of running MSX, and records hashes of the results so that builds can be
 * compared bit for bit.
 *
 *   bench FILE.inp FILE.msx [options]
 *   -mode M       how MSX is driven (default step):
 *                   step   ENopen, MSXopen, MSXsolveH, MSXinit(0), MSXstep loop, as a
 *                          toolkit program that reads results after every step does
 *                   solve  the same calls as runepanetmsx: MSXinit(1), MSXstep loop,
 *                          MSXreport, MSXsaveoutfile
 *                   read   step mode, also reading every node and link concentration of
 *                          every species with MSXgetqual after every step (timed, in Q)
 *                   info   no simulation: print the size and settings of the model
 *                          (counts and times only, no IDs or names) and exit
 *   -reps N       repeat the whole open..close N times in one process; report the minimum
 *   -check        hash every node and link concentration of every species after every
 *                 step (step mode); reading them is not timed
 *   -dump FILE    write every step's node and link concentrations as float64 to FILE
 *                 (first repetition only; implies -check)
 *   -dumpevery N  write only every Nth step to the dump (the hash still covers every step)
 *   -rpt FILE     EPANET report file (default /dev/null)
 *   -out FILE     MSX binary output file saved by MSXsaveoutfile (solve mode)
 *   -label STR    label echoed in the RESULT line
 *
 * Prints one line:
 *   RESULT label mode rc total open H Q report close steps hash maxrss_kb
 * Times are seconds (minimum over the repetitions). Q is MSXinit plus every MSXstep
 * (plus the reading in read mode). In info mode it prints one line INFO key=value ...
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <sys/resource.h>
#include "epanet2.h"
#include "epanetmsx.h"

static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+ts.tv_nsec*1e-9; }
static long max_rss(void){ struct rusage ru; getrusage(RUSAGE_SELF,&ru);
#ifdef __APPLE__
    return ru.ru_maxrss/1024;
#else
    return ru.ru_maxrss;
#endif
}
static uint64_t fnv(uint64_t h, const void *p, size_t n){ const unsigned char *c=p; while(n--){ h^=*c++; h*=1099511628211ULL; } return h; }

#define CHK(x) do{ int _e=(x); if(_e>0){ fprintf(stderr,"error %d at %s\n",_e,#x); rc=_e; goto done; } }while(0)
#define MINV(a,b) ((b)<(a)?(b):(a))

/* The size and settings of a model, without any ID or name */
static int info(const char *inp, const char *msx)
{
    int rc=0, nn=0, nt=0, nl=0, nc=0, nr=0, ns=0, np=0, nk=0, npat=0, i, t, bulk=0, wall=0;
    int junc=0, res=0, tank=0, pipe=0, pump=0, valve=0;
    long dur=0, hstep=0, qstep=0, rstep=0;
    char units[64];
    double at, rt;
    CHK(ENopen((char*)inp,"/dev/null",""));
    CHK(MSXopen((char*)msx));
    ENgetcount(EN_NODECOUNT,&nn); ENgetcount(EN_TANKCOUNT,&nt); ENgetcount(EN_LINKCOUNT,&nl);
    ENgetcount(EN_CONTROLCOUNT,&nc); ENgetcount(EN_RULECOUNT,&nr);
    for(i=1;i<=nn;i++){ ENgetnodetype(i,&t); if(t==EN_JUNCTION) junc++; else if(t==EN_RESERVOIR) res++; else tank++; }
    for(i=1;i<=nl;i++){ ENgetlinktype(i,&t); if(t<=EN_PIPE) pipe++; else if(t==EN_PUMP) pump++; else valve++; }
    ENgettimeparam(EN_DURATION,&dur); ENgettimeparam(EN_HYDSTEP,&hstep);
    ENgettimeparam(EN_QUALSTEP,&qstep); ENgettimeparam(EN_REPORTSTEP,&rstep);
    MSXgetcount(MSX_SPECIES,&ns); MSXgetcount(MSX_PARAMETER,&np); MSXgetcount(MSX_CONSTANT,&nk);
    MSXgetcount(MSX_PATTERN,&npat);
    for(i=1;i<=ns;i++){ MSXgetspecies(i,&t,units,&at,&rt); if(t==MSX_BULK) bulk++; else wall++; }
    printf("INFO junctions=%d reservoirs=%d tanks=%d pipes=%d pumps=%d valves=%d controls=%d rules=%d "
           "duration_s=%ld hydstep_s=%ld qualstep_s=%ld reportstep_s=%ld "
           "species_bulk=%d species_wall=%d parameters=%d constants=%d msx_patterns=%d\n",
           junc,res,tank,pipe,pump,valve,nc,nr,dur,hstep,qstep,rstep,bulk,wall,np,nk,npat);
done:
    MSXclose(); ENclose();
    return rc;
}

int main(int argc, char **argv)
{
    const char *inp=NULL,*msx=NULL,*rpt="/dev/null",*out=NULL,*mode="step",*label="-",*dumpf=NULL;
    int reps=1, check=0, every=1, i, r, rc=0;
    double best[6]={1e30,1e30,1e30,1e30,1e30,1e30};
    long steps=0; uint64_t hash=1469598103934665603ULL; FILE *df=NULL;
    for(i=1;i<argc;i++){
        if(!strcmp(argv[i],"-mode")&&i+1<argc) mode=argv[++i];
        else if(!strcmp(argv[i],"-reps")&&i+1<argc) reps=atoi(argv[++i]);
        else if(!strcmp(argv[i],"-check")) check=1;
        else if(!strcmp(argv[i],"-dump")&&i+1<argc){ dumpf=argv[++i]; check=1; }
        else if(!strcmp(argv[i],"-dumpevery")&&i+1<argc){ every=atoi(argv[++i]); if(every<1) every=1; }
        else if(!strcmp(argv[i],"-rpt")&&i+1<argc) rpt=argv[++i];
        else if(!strcmp(argv[i],"-out")&&i+1<argc) out=argv[++i];
        else if(!strcmp(argv[i],"-label")&&i+1<argc) label=argv[++i];
        else if(!inp) inp=argv[i];
        else if(!msx) msx=argv[i];
        else { fprintf(stderr,"unknown argument %s\n",argv[i]); return 2; }
    }
    if(!inp||!msx){ fprintf(stderr,"usage: bench FILE.inp FILE.msx [-mode step|solve|read|info] [-reps N] [-check] [-dump F] [-dumpevery N] [-rpt F] [-out F] [-label S]\n"); return 2; }
    if(!strcmp(mode,"info")) return info(inp,msx);
    int solve = !strcmp(mode,"solve"), readall = !strcmp(mode,"read");
    if(dumpf){ df=fopen(dumpf,"wb"); if(!df){ perror(dumpf); return 2; } }

    for(r=0;r<reps;r++){
        double t0,t1,t2,t3,t4,t5,tq=0,ta,tleft=1,t=0;
        int nn=0,nl=0,ns=0,j,m,first=(r==0);
        t0=now();
        CHK(ENopen((char*)inp,(char*)rpt,""));
        CHK(MSXopen((char*)msx));
        t1=now();
        CHK(MSXsolveH());
        t2=now();
        MSXgetcount(MSX_SPECIES,&ns); ENgetcount(EN_NODECOUNT,&nn); ENgetcount(EN_LINKCOUNT,&nl);
        if(first && df){ int32_t hd[4]={0x3158534d,nn,nl,ns}; fwrite(hd,sizeof hd,1,df); }
        ta=now();
        CHK(MSXinit(solve?1:0));
        tq+=now()-ta;
        steps=0;
        do{
            ta=now();
            CHK(MSXstep(&t,&tleft));
            if(readall){
                double v, sum=0;
                for(m=1;m<=ns;m++){
                    for(j=1;j<=nn;j++){ MSXgetqual(MSX_NODE,j,m,&v); sum+=v; }
                    for(j=1;j<=nl;j++){ MSXgetqual(MSX_LINK,j,m,&v); sum+=v; }
                }
                if(sum!=sum) fprintf(stderr,"NaN\n");
            }
            tq+=now()-ta;
            steps++;
            if(check && first){
                double v; int32_t tt=(int32_t)t;
                int dumpit = df && (steps % every == 0 || tleft <= 0);
                hash=fnv(hash,&tt,sizeof tt);
                if(dumpit) fwrite(&tt,sizeof tt,1,df);
                for(m=1;m<=ns;m++){
                    for(j=1;j<=nn;j++){ MSXgetqual(MSX_NODE,j,m,&v); hash=fnv(hash,&v,sizeof v); if(dumpit) fwrite(&v,sizeof v,1,df); }
                    for(j=1;j<=nl;j++){ MSXgetqual(MSX_LINK,j,m,&v); hash=fnv(hash,&v,sizeof v); if(dumpit) fwrite(&v,sizeof v,1,df); }
                }
            }
        }while(tleft>0);
        t3=t2+tq;
        ta=now();
        if(solve){
            CHK(MSXreport());
            if(out) CHK(MSXsaveoutfile((char*)out));
        }
        t4=now()-ta+t3;
        ta=now();
        MSXclose(); ENclose();
        t5=now()-ta+t4;
        best[0]=MINV(best[0],t5-t0); best[1]=MINV(best[1],t1-t0); best[2]=MINV(best[2],t2-t1);
        best[3]=MINV(best[3],t3-t2); best[4]=MINV(best[4],t4-t3); best[5]=MINV(best[5],t5-t4);
        if(df){ fclose(df); df=NULL; }
    }
done:
    printf("RESULT %s %s %d %.6f %.6f %.6f %.6f %.6f %.6f %ld %016llx %ld\n", label, mode, rc,
           best[0],best[1],best[2],best[3],best[4],best[5], steps,
           (unsigned long long)(check?hash:0), max_rss());
    return rc;
}
