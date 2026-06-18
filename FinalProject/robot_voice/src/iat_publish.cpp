/*
* 语音听写(iFly Auto Transform)技术能够实时地将语音转换成对应的文字。
*/

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <termio.h>
#include "qisr.h"
#include "msp_cmn.h"
#include "msp_errors.h"
#include "speech_recognizer.h"
#include <iconv.h>

#include "ros/ros.h"
#include "std_msgs/String.h"

#define FRAME_LEN   640 
#define BUFFER_SIZE 4096

int wakeupFlag   = 0 ;
int resultFlag   = 0 ;

static void show_result(char *string, char is_over)
{
    resultFlag=1;   
    printf("\rResult: [ %s ]", string);
    if(is_over)
        putchar('\n');
}

static char *g_result = NULL;
static unsigned int g_buffersize = BUFFER_SIZE;

void on_result(const char *result, char is_last)
{
    if (result) {
        size_t left = g_buffersize - 1 - strlen(g_result);
        size_t size = strlen(result);
        if (left < size) {
            g_result = (char*)realloc(g_result, g_buffersize + BUFFER_SIZE);
            if (g_result)
                g_buffersize += BUFFER_SIZE;
            else {
                printf("mem alloc failed\n");
                return;
            }
        }
        strncat(g_result, result, size);
        show_result(g_result, is_last);
    }
}

void on_speech_begin()
{
    // 开始录音前强制清空
    if (g_result)
    {
        free(g_result);
        g_result = NULL;
    }
    g_result = (char*)malloc(BUFFER_SIZE);
    g_buffersize = BUFFER_SIZE;
    memset(g_result, 0, g_buffersize);

    printf("Start Listening...\n");
    printf("Press \"Space\" key Stop\n");
}

void on_speech_end(int reason)
{
    if (reason == END_REASON_VAD_DETECT)
        printf("\nSpeaking done \n");
    else
        printf("\nRecognizer error %d\n", reason);
}

/* demo recognize the audio from microphone */
static void demo_mic(const char* session_begin_params)
{
    int errcode;
    int i = 0;

    struct speech_rec iat;

    struct speech_rec_notifier recnotifier = {
        on_result,
        on_speech_begin,
        on_speech_end
    };

    errcode = sr_init(&iat, session_begin_params, SR_MIC, &recnotifier);
    if (errcode) {
        printf("speech recognizer init failed\n");
        return;
    }
    errcode = sr_start_listening(&iat);
    if (errcode) {
        printf("start listen failed %d\n", errcode);
    }

    int ch;
    while(1){
        ch = getchar();
        if(ch == 32){
            printf("\nSpeaking done \n");
            break;
        }
    }
    errcode = sr_stop_listening(&iat);
    if (errcode) {
        printf("stop listening failed %d\n", errcode);
    }

    sr_uninit(&iat);
}


int main(int argc, char* argv[])
{
    ros::init(argc, argv, "iFlyAutoTransform");
    ros::NodeHandle n;
    ros::Rate loop_rate(10);  
    // 话题 /voice_words 与解析节点完全对应
    ros::Publisher voice_words_pub = n.advertise<std_msgs::String>("/voice_words", 1000);  

    termios tms_old, tms_new;
    tcgetattr(0, &tms_old); 
    tms_new = tms_old;
    tms_new.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(0, TCSANOW, &tms_new);

    ROS_INFO("Press \"Space\" key to Start,Press \"Enter\" key to Exit.");
    int count=0;
    int ch;
    while(ros::ok())
    {
        ch = getchar();
        printf("Pressed Key Value %d\n",ch);
        if(ch == 32){  //Space key
            wakeupFlag = 1;
        }
        if(ch == 10){  //Enter key
            ROS_INFO("Node Exit.");
            break;
        }
        if (wakeupFlag){
            int ret = MSP_SUCCESS;
            /* 讯飞完整密钥配置 */
            const char* login_params = "appid=2fa4d226,app_key=1a96d75ea8c182ecf565c1a79277d77c,app_secret=ZmE4YTYwODQ1YzRmMjhkZThlM2ZlNWY4,work_dir=.";

            const char* session_begin_params =
                "sub = iat, domain = iat, language = zh_cn, "
                "accent = mandarin, sample_rate = 16000, "
                "result_type = plain, result_encoding = utf8";

            ret = MSPLogin(NULL, NULL, login_params);
            if(MSP_SUCCESS != ret){
                MSPLogout();
                printf("MSPLogin failed , Error code %d.\n",ret);
            }
            printf("Demo recognizing the speech from microphone\n");
            demo_mic(session_begin_params);
            wakeupFlag=0;
            MSPLogout();
        }

        // 识别完成发布话题 + 释放内存防乱码/残留
        if(resultFlag){
            resultFlag=0;
            std_msgs::String msg;
            if(g_result != NULL)
            {
                msg.data = g_result;
                voice_words_pub.publish(msg);
                // 发布后立即释放
                free(g_result);
                g_result = NULL;
            }
        }

        ROS_INFO("Press \"Space\" key to Start,Press \"Enter\" key to Exit.");
        ros::spinOnce();
        loop_rate.sleep();
        count++;
    }

exit:
    tcsetattr(0, TCSANOW, &tms_old);
    if(g_result != NULL)
    {
        free(g_result);
        g_result = NULL;
    }
    MSPLogout();
    return 0;
}

