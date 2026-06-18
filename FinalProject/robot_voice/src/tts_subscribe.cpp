/*
* 语音合成（Text To Speech，TTS）技术能够自动将任意文字实时转换为连续的
* 自然语音，是一种能够在任何时间、任何地点，向任何人提供语音信息服务的
* 高效便捷手段，非常符合信息时代海量数据、动态更新和个性化查询的需求。
*/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>

#include "qtts.h"
#include "msp_cmn.h"
#include "msp_errors.h"

#include "ros/ros.h"
#include "std_msgs/String.h"

#include <sstream>
#include <sys/types.h>
#include <sys/stat.h>


/* wav音频头部格式 */
typedef struct _wave_pcm_hdr
{
    char            riff[4];
    int     size_8;
    char            wave[4];
    char            fmt[4];
    int     fmt_size;

    short int       format_tag;
    short int       channels;
    int     samples_per_sec;
    int     avg_bytes_per_sec;
    short int       block_align;
    short int       bits_per_sample;

    char            data[4];
    int     data_size;
} wave_pcm_hdr;

/* 默认wav音频头部数据 */
wave_pcm_hdr default_wav_hdr = 
{
    { 'R', 'I', 'F', 'F' },
    0,
    {'W', 'A', 'V', 'E'},
    {'f', 'm', 't', ' '},
    16,
    1,
    1,
    16000,
    32000,
    2,
    16,
    {'d', 'a', 't', 'a'},
    0  
};

/* 文本合成 */
int text_to_speech(const char* src_text, const char* des_path, const char* params)
{
    int          ret          = -1;
    FILE*        fp           = NULL;
    const char*  sessionID    = NULL;
    unsigned int audio_len    = 0;
    wave_pcm_hdr wav_hdr      = default_wav_hdr;
    int          synth_status = MSP_TTS_FLAG_STILL_HAVE_DATA;

    if (NULL == src_text || NULL == des_path)
    {
        printf("params is error!\n");
        return ret;
    }
    fp = fopen(des_path, "wb");
    if (NULL == fp)
    {
        printf("open %s error.\n", des_path);
        return ret;
    }
    /* 开始合成 */
    sessionID = QTTSSessionBegin(params, &ret);
    if (MSP_SUCCESS != ret)
    {
        printf("QTTSSessionBegin failed, error code: %d.\n", ret);
        fclose(fp);
        return ret;
    }
    ret = QTTSTextPut(sessionID, src_text, (unsigned int)strlen(src_text), NULL);

    if (MSP_SUCCESS != ret)
    {
        printf("QTTSTextPut failed, error code: %d.\n",ret);
        QTTSSessionEnd(sessionID, "TextPutError");
        fclose(fp);
        return ret;
    }
    printf("正在合成 ...\n");
    fwrite(&wav_hdr, sizeof(wav_hdr) ,1, fp);
    while (1) 
    {
        const void* data = QTTSAudioGet(sessionID, &audio_len, &synth_status, &ret);
        if (MSP_SUCCESS != ret)
            break;
        if (NULL != data)
        {
            fwrite(data, audio_len, 1, fp);
            wav_hdr.data_size += audio_len;
        }
        if (MSP_TTS_FLAG_DATA_END == synth_status)
            break;
        printf(">");
        usleep(150*1000);
    }
    printf("\n");
    if (MSP_SUCCESS != ret)
    {
        printf("QTTSAudioGet failed, error code: %d.\n",ret);
        QTTSSessionEnd(sessionID, "AudioGetError");
        fclose(fp);
        return ret;
    }
    /* 修正wav文件头数据的大小 */
    wav_hdr.size_8 += wav_hdr.data_size + (sizeof(wav_hdr) - 8);
    
    fseek(fp, 4, 0);
    fwrite(&wav_hdr.size_8,sizeof(wav_hdr.size_8), 1, fp);
    fseek(fp, 40, 0);
    fwrite(&wav_hdr.data_size,sizeof(wav_hdr.data_size), 1, fp);
    fclose(fp);
    fp = NULL;
    ret = QTTSSessionEnd(sessionID, "Normal");
    if (MSP_SUCCESS != ret)
    {
        printf("QTTSSessionEnd failed, error code: %d.\n",ret);
    }

    return ret;
}

void ttsCallback(const std_msgs::String::ConstPtr& msg)
{
    ROS_INFO("收到播报内容：%s", msg->data.c_str());
    const char* text;
    int         ret                  = MSP_SUCCESS;
    const char* session_begin_params = "voice_name=xiaoyan,text_encoding=utf8,sample_rate=16000,speed=50,volume=80,pitch=50,rdn=2";
    // 固定生成到桌面，绝对路径
    const char* filename             = "/home/turing/Desktop/tts_sample.wav";

    std::cout<<"收到文本: "<<msg->data.c_str()<<std::endl;
    text = msg->data.c_str(); 

    printf("开始合成语音...\n");
    ret = text_to_speech(text, filename, session_begin_params);
    if (MSP_SUCCESS != ret)
    {
        printf("合成失败, error code: %d.\n", ret);
        return;
    }
    printf("合成完成，开始播放\n");
    // 使用系统自带 aplay 播放，无需额外安装
    system("aplay -q /home/turing/Desktop/tts_sample.wav");
    sleep(1);
}

void toExit()
{
    printf("按任意键退出 ...\n");
    getchar();
    MSPLogout();
}

int main(int argc, char* argv[])
{
    int         ret                  = MSP_SUCCESS;
    // 讯飞完整登录密钥（已配置正确）
    const char* login_params = "appid=2fa4d226,app_key=1a96d75ea8c182ecf565c1a79277d77c,app_secret=ZmE4YTYwODQ1YzRmMjhkZThlM2ZlNWY4,work_dir=.";

    ret = MSPLogin(NULL, NULL, login_params);
    if (MSP_SUCCESS != ret)
    {
        printf("MSPLogin 登录失败, error code: %d.\n", ret);
        toExit();
    }
    printf("\n###########################################################################\n");
    printf("## 讯飞语音合成 TTS 已就绪 ##\n");
    printf("###########################################################################\n\n");

    ros::init(argc,argv,"TextToSpeech");
    ros::NodeHandle n;
    // 订阅话题 /voice_talk
    ros::Subscriber tts_sub = n.subscribe("/voice_talk", 1000, ttsCallback);
    ros::spin();

exit:
    MSPLogout();
    return 0;
}

