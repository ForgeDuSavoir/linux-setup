/* Test-only libc interposition: private fixture syscalls, never installed. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int exchanged;
int renameat2(int a, const char *x, int b, const char *y, unsigned flags) {
    int (*real)(int,const char*,int,const char*,unsigned)=dlsym(RTLD_NEXT,"renameat2");
    const char *fault=getenv("R7_FAULT");
    if (fault && !strcmp(fault,"before")) { errno=EIO; return -1; }
    if (fault && !strcmp(fault,"late-edit")) {
        FILE *f=fopen(y,"a"); if(f) {fputs("\n ",f); fclose(f);}
    }
    int result=real(a,x,b,y,flags);
    if (!result) exchanged=1;
    if (!result && fault && !strcmp(fault,"lost-reply")) { errno=EIO; return -1; }
    return result;
}
int fsync(int fd) {
    int (*real)(int)=dlsym(RTLD_NEXT,"fsync");
    const char *fault=getenv("R7_FAULT");
    if(exchanged && fault && !strcmp(fault,"after")) {errno=EIO;return -1;}
    return real(fd);
}
