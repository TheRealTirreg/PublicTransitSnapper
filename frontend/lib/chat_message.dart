/// Copyright 2022
/// Bachelor's thesis by Gerrit Freiwald and Robin Wu

class ChatMessage{
  int userId;
  String userName;
  String messageContent;
  String timeSent;
  ChatMessage({
    required this.userId,
    required this.userName,
    required this.messageContent,
    required this.timeSent,
  });
}