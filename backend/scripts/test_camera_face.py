# backend/scripts/test_camera_face.py
import cv2
import face_recognition

def main():
    # 1. 打开电脑的默认摄像头 (数字 0 代表自带摄像头，如果是外接USB摄像头可以改成 1)
    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("无法打开摄像头，请检查设备连接或权限设置。")
        return

    print("摄像头已启动！")
    print("👉 请正对摄像头，识别到人脸后会画出红框。")
    print("👉 按下键盘上的 'q' 键退出，系统将自动为你保存一张截图用于中期报告！")

    while True:
        # 2. 抓取一帧视频画面
        ret, frame = video_capture.read()
        if not ret:
            print("无法获取视频帧，退出...")
            break

        # 3. 将 OpenCV 默认的 BGR 颜色格式转换为 face_recognition 需要的 RGB 格式
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 4. 调用核心算法：找到当前画面中所有的人脸位置
        # 返回结果是一个列表，包含每个人脸的 (top, right, bottom, left) 坐标
        face_locations = face_recognition.face_locations(rgb_frame)

        # 5. 遍历找到的每一张人脸，并在原图上画框
        for top, right, bottom, left in face_locations:
            # 画一个红色的矩形框 (OpenCV 是 BGR 格式，所以 (0, 0, 255) 是红色)
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            
            # 在人脸框上方写上绿色的提示文字
            cv2.putText(frame, "Face Detected", (left, top - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 6. 实时显示画面
        cv2.imshow('SnapSign - Face Detection Demo', frame)

        # 7. 监听键盘事件：按 'q' 键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            # 自动保存当前帧为高清截图，直接用于中期报告
            screenshot_name = 'midterm_report_fig3.jpg'
            cv2.imwrite(screenshot_name, frame)
            print(f"\n✅ 退出成功！已为你自动保存截图：{screenshot_name}")
            break

    # 8. 释放摄像头资源并关闭窗口
    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()