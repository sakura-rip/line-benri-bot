from linepy import (
                LINE,
                OEPoll
            )
from akad.ttypes import (
                OpType,
                MIDType,
                contentType
            )
import re
import time
import json
import requests


class Main():
    def __init__(self):
        self.msgcmd = MessageFunction(self)
        self.action = OperationFunction(self)
        self.ops = Operation(self)
        self.sakura = LINE()
        self.mid = self.sakura.profile.mid
        self.sett = self.sakura.getSettings()
        self.help = """mid
>>>個人アカウントのid
gid
>>>グループのid
leave
>>>グループから抜ける
curl
>>>グループうらる拒否
ourl
>>>グループうらる許可
ginfo
>>>グループ情報
gcreator
>>>グループ作成者
setpoint
>>>既読ポイント設置
delpoint
>>>既読ポイント破棄
checkread
>>>既読確認
help
>>>helpを表示
url
>>>追加URLを発行
mid @
>>>メンションした人のmid確認"""
        self.poll = OEPoll(self.sakura)
        self.timesleep = {}
        self.checkread = {}

    def running(self):
        while True:
            try:
                ops = self.poll.singleTrace(count=50)
                if ops:
                    for op in ops:
                        self.poll.setRevision(op.revision)
                        self.ops.getOperation(op)
            except Exception as e:
                print(e)

    def check_time(self, to):
        if to in self.timesleep:
            if time.time() - self.timesleep[to] < 3:
                return False
            else:
                self.timesleep[to] = time.time()
                return True


class Operation():
    def __init__(self, main):
        self.main = main

    def getOperation(self, op):
        try:
            if op.type == OpType.END_OF_OPERATION:
                return
            elif op.type == OpType.RECEIVE_MESSAGE:
                self.main.action.RECEIVE_MESSAGE(op)
            elif op.type == OpType.NOTIFIED_ADD_CONTACT:
                self.main.action.NOTIFIED_ADD_CONTACT(op)
            elif op.type == OpType.NOTIFIED_INVITE_INTO_GROUP:
                self.main.action.NOTIFIED_INVITE_INTO_GROUP(op)
            elif op.type == OpType.NOTIFIED_READ_MESSAGE:
                self.main.action.NOTIFIED_READ_MESSAGE(op)
        except Exception as e:
            print(e)


class OperationFunction():
    def __init__(self, main):
        self.main = main

    def NOTIFIED_READ_MESSAGE(self, op):
        if op.param1 in self.main.checkread:
            if op.param2 not in self.main.checkread[op.param1]:
                self.main.checkread[op.param1].append(op.param2)

    def RECEIVE_MESSAGE(self, op):
        msg = op.message
        if msg.contentType == contentType.NONE and msg.toType == MIDType.GROUP:
            if msg.text in self.main.msgcmd.command:
                if self.main.check_time(msg.tp):
                    self.main.msgcmd.command[msg.text.lower()](msg)
            elif msg.text.startswith(tuple(self.main.msgcmd.startswith_command.keys())):
                cmds = [
                    x for x in self.main.msgcmd.startswith_command if msg.text.startswith(x)]
                if self.main.check_time(msf.to):
                    self.main.msgcmd.startswith_command[cmds[0]](msg)
            elif len(msg.text) > 32:
                if self.main.check_time(msg.to):
                    try:
                        self.main.msgcmd.sendCon(msg)
                    except:
                        pass
                    try:
                        self.main.msgcmd.sendGrp(msg)
                    except:
                        pass
        elif msg.contentType == contentType.CONTACT:
            if self.main.check_time(msg.to):
                self.main.msgcmd.contactInfo(msg)

    def NOTIFIED_ADD_CONTACT(self, op):
        pass  # ほんとはここにある

    def NOTIFIED_INVITE_INTO_GROUP(self, op):
        if self.main.mid in op.param3:
            self.main.sakura.acceptGroupInvitation(op.param1)
            self.main.sakura.sendMessage(
                op.param1, "はじめまして!!\n便利ボットです\n連投対策として3秒間の空きが必要です\nコマンドはhelpで確認できます\n誰でも使用可能なのでお気軽にグループにお誘いください")


class MessageFunction():
    def __init__(self, main):
        self.main = main
        self.command = {
            "mid": self.yourMid,
            "leave": self.leave,
            "gid": self.groupId,
            "curl": self.curl,
            "ourl": self.ourl,
            "ginfo": self.groupInfo,
            "gurl": self.gurl,
            "gcreator": self.gcreator,
            "setpoint": self.setpoint,
            "delpoint": self.delpoint,
            "checkread": self.checkpoint,
            "help": self.sendhelp,
            "url": self.addurl
        }
        self.startswith_command = {
            "mid ": self.getmid
        }

    def sendhelp(self, msg):
        self.main.sakura.sendMessage(msg.to, self.main.help)

    def getIdFromStr(self, msg, types="mid"):
        if types == "mid":
            pattrn = r"u\w{32}"
        elif types == "gid":
            pattrn = r"c\w{32}"
        else:
            return []
        ids = re.findall(pattrn, msg.text)
        return ids

    def sendCon(self, msg):
        tar = self.getIdFromStr(msg, "mid")
        if tar:
            for mid in tar:
                time.sleep(0.1)
                self.main.sakura.sendContact(msg.to, mid)

    def addurl(self, msg):
        if self.main.sett.contactMyTicket:
            self.main.sakura.sendMessage(msg.to, f"line.me/ti/p/{self.main.sett.contactMyTicket}")
        else:
            self.main.sakura.sendMessage(msg.to, f"line.me/ti/p/{self.main.sakura.reissueUserTicket()}")

    def yourMid(self, msg):
        self.main.sakura.sendMessage(msg.to, msg._from)

    def sendGrp(self, msg):
        tar = self.getIdFromStr(msg, "gid")
        txt = ""
        if tar:
            for gid in tar:
                grp = self.main.sakura.getCompactGroup(gid)
                url = "OPEN" if not grp.preventedJoinByTicket == True else "CLOSE"
                txt += f"Group Name : {grp.name}\n"
                txt += f"Group Invitee : {len(grp.invitee) if grp.invitee else 0}\n"
                txt += f"Group Members : {len(grp.members)}\n"
                txt += f"Group Ticket : {url}\n\n"
                txt += f"Total : {len(tar)}"
            self.main.sakura.sendMessage(msg.to, txt)

    def contactInfo(self, msg):
        if 'displayName' in msg.contentMetadata:
            mid = msg.contentMetadata['mid']
            con = self.main.sakura.getContact(mid)
            txt = f"mid : {mid}\ndisplayName : {con.displayName}"
            self.main.sakura.sendMessage(msg.to, txt)

    def setpoint(self, msg):
        self.main.checkread[msg.to] = []
        self.main.sakura.sendMessage(msg.to, "Set Ok")

    def checkpoint(self, msg):
        if msg.to in self.main.checkread:
            cons = self.main.sakura.getContacts(self.main.checkread[msg.to])
            txt = "\n".join([con.displayName for con in cons])
            txt += f"\n{len(cons)}人が既読しました"
            self.main.sakura.sendMessage(msg.to, txt)

    def delpoint(self, msg):
        if msg.to in self.main.checkread:
            del self.main.checkread[msg.to]
            self.main.sakura.sendMessage(msg.to, "Del Ok")
        else:
            self.main.sakura.sendMessage(msg.to, "No Point")

    def groupInfo(self, msg):
        grp = self.main.sakura.getCompactGroup(msg.to)
        url = "OPEN" if not grp.preventedJoinByTicket == True else "CLOSE"
        txt = f"Group Name : {grp.name}\n"
        txt += f"Group Id : {grp.id}\n"
        txt += f"Group Invitee : {len(grp.invitee) if grp.invitee else 0}\n"
        txt += f"Group Members : {len(grp.members)}\n"
        txt += f"Group Ticket : {url}"
        self.main.sakura.sendMessage(msg.to, txt)

    def mention(self, msg):
        if "MENTION" in msg.contentMetadata:
            key = eval(msg.contentMetadata["MENTION"])
            return [x["M"] for x in key["MENTIONEES"]]
        else:
            return []

    def getmid(self, msg):
        for mid in self.mention(msg):
            self.main.sakura.sendMessage(msg.to, mid)

    def leave(self, msg):
        self.main.sakura.leaveGroup(msg.to)

    def groupId(self, msg):
        self.main.sakura.sendMessage(msg.to, msg.to)

    def gurl(self, msg):
        self.main.sakura.sendMessage(msg.to, f"https://line.me/R/ti/g/{self.main.sakura.reissueGroupTicket(msg.to)}")

    def ourl(self, msg):
        grp = self.main.sakura.getGroup(msg.to)
        if grp.preventedJoinByTicket:
            grp.preventedJoinByTicket = False
            self.main.sakura.updateGroup(grp)
            self.main.sakura.sendMessage(msg.to, "開きました")
        else:
            self.main.sakura.sendMessage(msg.to, "既に開いています")

    def curl(self, msg):
        grp = self.main.sakura.getGroup(msg.to)
        if grp.preventedJoinByTicket == False:
            grp.preventedJoinByTicket = True
            self.main.sakura.updateGroup(grp)
            self.main.sakura.sendMessage(msg.to, "閉じました")
        else:
            self.main.sakura.sendMessage(msg.to, "既に閉じています")

    def gcreator(self, msg):
        grp = self.main.sakura.getGroup(msg.to)
        if grp.creator:
            self.main.sakura.sendContact(msg.to, grp.creator.mid)
        else:
            self.main.sakura.sendMessage(msg.to, "削除済みです")


if __name__ == '__main__':
    main = Main()
    main.running()
