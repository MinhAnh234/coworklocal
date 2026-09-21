"""Bấm "Dừng" phải thấy được là nó đã ăn.

Triệu chứng người dùng báo: một lượt chạy đã 159 giây, bấm Dừng, rồi không có
gì đổi trên màn hình — chỉ báo vẫn đếm "Đang chạy · 160s", nên không biết nút
có tác dụng hay không.

Hai chỗ nói sai, cả hai đều kiểm được:

* Lúc bấm — ``stop()`` chỉ đặt cờ huỷ trên worker rồi thôi. Huỷ thật có thể mất
  vài giây (đang chờ gateway trả lời, đang chạy dở một tool), mà trong khoảng đó
  màn hình vẫn nói "Đang chạy".
* Lúc kết thúc — ``_on_finished`` luôn đặt dấu XANH "Đã hoàn thành", kể cả khi
  lượt chạy vừa bị người dùng dừng. Dấu đó nói ngược hẳn với thứ vừa xảy ra.

Gọi thẳng phương thức với một ``self`` giả, không dựng ``ChatPanel`` thật: những
hàm này là Python thuần trên vài thuộc tính của chính nó, và dựng cả màn chat
trong ``tests/ui`` kéo theo QtWebEngine (xem
``test_graphrag_follows_folder_change.py``).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="cần PySide6 để nạp module")

from cowork_local.presentation.chat.chat_panel import ChatPanel
from cowork_local.presentation.chat.chat_turn_runner import ChatTurnRunnerMixin


class _ChiBaoGia:
    """Thay ``ThinkingIndicator`` — ghi lại nhãn nó được yêu cầu hiện."""

    def __init__(self):
        self.nhan = []

    def set_label(self, key):
        self.nhan.append(key)

    def start(self, key="chat.running"):
        self.nhan.append(key)

    def stop(self):
        self.nhan.append(None)


class _KhungChatGia:
    """Thay ``chat_view`` — ghi lại loại dấu kết thúc được đặt vào."""

    def __init__(self):
        self.dau = []

    def add_error(self, text):
        self.dau.append(("error", text))
        return object()

    def add_status(self, text):
        self.dau.append(("status", text))
        return object()

    def add_success(self, text):
        self.dau.append(("success", text))
        return object()


class _WorkerGia:
    def __init__(self, dang_chay=True):
        self._dang_chay = dang_chay
        self.da_yeu_cau_dung = False

    def isRunning(self):
        return self._dang_chay

    def request_stop(self):
        self.da_yeu_cau_dung = True


class _ComposerGia:
    def __init__(self):
        self.da_xoa_hang_doi = False

    def clear_queue(self):
        self.da_xoa_hang_doi = True

    def set_running(self, _v):
        pass

    def set_busy(self, _v):
        pass

    def set_text(self, _v):
        pass


class _TinNhanGia:
    def __init__(self):
        self.da_phat = []

    def emit(self, *args):
        self.da_phat.append(args[0] if len(args) == 1 else args)


class _Panel:
    """``self`` giả cho các phương thức đang kiểm."""

    kind = "cowork"

    def __init__(self, dang_chay=True):
        self.worker = _WorkerGia(dang_chay)
        self._active = {self.worker: {}} if dang_chay else {}
        self.composer = _ComposerGia()
        self.status_message = _TinNhanGia()
        self.turn_finished = _TinNhanGia()
        self.graph_event = _TinNhanGia()
        self.session_name = "test"
        self.thinking = _ChiBaoGia()
        self.chat_view = _KhungChatGia()
        self._stop_requested = False
        self._ban_ron = dang_chay

    def _view_busy(self):
        return self._ban_ron

    def _max_parallel(self):
        return 2

    # -- những thứ _on_failed cần, đều là no-op ------------------------- #
    def _turn_is_live(self, _ctx):
        return True

    def _end_turn(self, _ctx):
        pass

    def _cleanup_turn(self, _ctx, _ok):
        pass

    def _drain_queue(self):
        pass

    def _persist_session(self, _ctx):
        pass

    def _dau_ket_thuc(self):
        """Gọi phương thức THẬT — đây là thứ đang được kiểm, không giả lập.

        Tra tên lúc GỌI chứ không lúc dựng lớp: tra lúc dựng thì trên bản
        chưa sửa cả file test đổ ngay ở khâu thu thập, và một lỗi thu thập
        không nói được gì về hành vi.
        """
        return ChatTurnRunnerMixin._dau_ket_thuc(self)



# ---- lúc bấm Dừng -------------------------------------------------------

def test_bam_dung_thi_chi_bao_doi_sang_dang_dung():
    """Đây là chỗ hỏng người dùng thấy: bấm xong màn hình không đổi gì."""
    p = _Panel()

    ChatTurnRunnerMixin.stop(p)

    assert p._stop_requested is True
    assert "chat.stopping" in p.thinking.nhan, (
        "chỉ báo vẫn nói 'Đang chạy' — người dùng đọc ra là nút Dừng không ăn")


def test_bam_dung_van_yeu_cau_worker_dung_va_xoa_hang_doi():
    """Hành vi vốn có, không được mất khi thêm phần hiển thị."""
    p = _Panel()

    ChatTurnRunnerMixin.stop(p)

    assert p.worker.da_yeu_cau_dung is True
    assert p.composer.da_xoa_hang_doi is True


def test_khong_co_luot_nao_chay_thi_bam_dung_khong_lam_gi():
    """Không có gì để dừng thì đừng nói dối là đang dừng."""
    p = _Panel(dang_chay=False)

    ChatTurnRunnerMixin.stop(p)

    assert p._stop_requested is False
    assert p.thinking.nhan == []


# ---- lúc lượt chạy kết thúc --------------------------------------------

def test_da_dung_thi_dat_dau_da_dung_chu_khong_phai_hoan_thanh():
    p = _Panel()
    p._stop_requested = True

    ChatTurnRunnerMixin._dau_ket_thuc(p)

    loai, text = p.chat_view.dau[0]
    assert loai == "status", "dừng theo yêu cầu mà vẫn đặt dấu xanh 'Đã hoàn thành'"
    assert "dừng" in text.lower() or "stop" in text.lower(), text


def test_ket_thuc_binh_thuong_van_dat_dau_hoan_thanh():
    """Chặn một chiều là hỏng tính năng — lượt chạy xong xuôi vẫn phải xanh."""
    p = _Panel()

    ChatTurnRunnerMixin._dau_ket_thuc(p)

    assert p.chat_view.dau[0][0] == "success"


# ---- đồng bộ lại chỉ báo (đổi tab, Refresh History) --------------------

def test_dong_bo_lai_khong_keo_nhan_ve_dang_chay():
    """``_sync_indicators`` chạy lại khi chuyển tab; nó mà đặt lại
    "chat.running" là nhãn "đang dừng" bị xoá ngay sau khi bấm."""
    p = _Panel()
    p._stop_requested = True

    ChatPanel._sync_indicators(p)

    assert p.thinking.nhan[-1] == "chat.stopping"


def test_dong_bo_lai_khi_chua_bam_dung_thi_van_la_dang_chay():
    p = _Panel()

    ChatPanel._sync_indicators(p)

    assert p.thinking.nhan[-1] == "chat.running"



# ---- lượt chạy kết thúc bằng NGOẠI LỆ vì vừa bị huỷ --------------------

def test_da_bam_dung_thi_loi_luc_huy_hien_ra_la_da_dung():
    """Đúng thứ người dùng chụp lại: bấm Dừng xong nhận một dòng đỏ
    "'NoneType' object has no attribute 'read'" — đó là hệ quả của chính việc
    huỷ (đóng socket giữa stream), không phải một lỗi cần báo."""
    p = _Panel()
    p._stop_requested = True

    ChatTurnRunnerMixin._on_failed(p, {}, "'NoneType' object has no attribute 'read'")

    loai = [l for l, _ in p.chat_view.dau]
    assert "error" not in loai, "vẫn dội lỗi Python ra màn hình sau khi người dùng bấm Dừng"
    assert loai == ["status"]
    assert "dừng" in p.chat_view.dau[0][1].lower()


def test_loi_that_khi_chua_bam_dung_van_bao_loi_nhu_cu():
    """Chặn một chiều là nuốt mất lỗi thật."""
    p = _Panel()

    ChatTurnRunnerMixin._on_failed(p, {}, "gateway 500")

    assert p.chat_view.dau == [("error", "gateway 500")]


def test_thanh_trang_thai_noi_cung_mot_chuyen_voi_khung_chat():
    p = _Panel()
    p._stop_requested = True

    ChatTurnRunnerMixin._on_failed(p, {}, "bat ky loi gi")

    assert any("dừng" in t.lower() for t in p.status_message.da_phat), p.status_message.da_phat

# ---- i18n ---------------------------------------------------------------

@pytest.mark.parametrize("key", ["chat.stopping", "chat.stopped_marker",
                                 "chatpanel.stopped"])
def test_key_moi_co_du_ba_ngon_ngu(key):
    from cowork_local import i18n

    entry = i18n.STRINGS[key]
    for lang in ("en", "ja", "vi"):
        assert entry.get(lang), f"{key} thiếu {lang}"
