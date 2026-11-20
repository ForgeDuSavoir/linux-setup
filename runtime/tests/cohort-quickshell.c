/* Private native fake shell: matching /proc/exe, no QML/UI/bus. Test-only. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
static void path(char *out,const char *name){snprintf(out,4096,"%s/%s",getenv("HOME"),name);}
int main(int argc,char **argv){
 char file[4096],cfg[4096];path(file,"qs.pid");snprintf(cfg,sizeof cfg,"%s/.config/quickshell/shell.qml",getenv("HOME"));
 char log[4096];path(log,"qs.calls");FILE *l=fopen(log,"a");fprintf(l,"%s\n",argc>1?argv[1]:"bar");fclose(l);
 if(argc>1&&!strcmp(argv[1],"list")){
   FILE *f=fopen(file,"r");int pid;if(f&&fscanf(f,"%d",&pid)==1)printf("Instance fixture:\n Process ID: %d\n Config path: %s\n",pid,cfg);if(f)fclose(f);return 0;
 }
 if(argc>1&&!strcmp(argv[1],"kill")){
   if(argc!=4||strcmp(argv[2],"--pid"))return 9;
   kill(atoi(argv[3]),SIGTERM);unlink(file);return 0;
 }
 if(argc>1&&!strcmp(argv[1],"--daemonize")){
   pid_t pid=fork();if(pid<0)return 10;
   if(pid){FILE *f=fopen(file,"w");fprintf(f,"%d",pid);fclose(f);return 0;}
   int null=open("/dev/null",O_RDWR);for(int i=0;i<3;i++)dup2(null,i);if(null>2)close(null);
   for(;;)pause();
 }
 return 0;
}
