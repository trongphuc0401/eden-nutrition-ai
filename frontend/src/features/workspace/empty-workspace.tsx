import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";

export function EmptyWorkspace({ selectIngredients, start, blocked }: { selectIngredients: () => void; start: () => void; blocked: boolean }) {
  return (
    <div className="grid min-h-[420px] place-items-center rounded-card border border-dashed border-line bg-warm p-6 text-center">
      <div className="max-w-lg">
        <span className="mx-auto grid size-16 place-items-center rounded-3xl bg-orange-soft text-brand"><Icon name="cup" className="size-8" /></span>
        <h2 className="mt-5 text-2xl font-semibold text-strong">Chọn trái cây cho ly sinh tố hôm nay</h2>
        <p className="mt-3 leading-7 text-muted">Bắt đầu từ nguyên liệu theo vùng của bạn. AI chỉ dùng danh sách bạn xác nhận và kiểm tra lại dị ứng, sở thích cùng ràng buộc dinh dưỡng.</p>
        {blocked && <p className="mt-5 rounded-xl border border-yellow-line bg-yellow-soft p-4 text-left text-sm leading-6 text-yellow-text">Hồ sơ hiện ngoài phạm vi thử nghiệm (BMI ≥ 23). Bạn vẫn có thể hỏi trợ lý về dinh dưỡng, nhưng chưa tạo được công thức.</p>}
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <Button onClick={selectIngredients}>Chọn nguyên liệu</Button>
          <Button variant="primary" onClick={start} disabled={blocked}>Tạo báo cáo PDF</Button>
        </div>
      </div>
    </div>
  );
}
