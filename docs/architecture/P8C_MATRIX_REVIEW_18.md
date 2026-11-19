# #18 — контрольная точка до сдачи #17

Вердикт: ревью заблокировано, а не отклонено. В [#17](https://git.aiopslab.online/aiopslab/otus-diplom/issues/17) на момент проверки нет сдачи; в списке PR нет матрицы. SHA матрицы не установлен. Нельзя оценить ни одну строку как принятую.

[§6 дорожной карты](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/d22aa8f1170deaf09580518916ea02c7c4d8bfba/docs/architecture/P8_PORTAL_IMPLEMENTATION_ROADMAP.md#L193-L196) задаёт четыре результата: `PORTAL_UI = RUNNING`, `PORTAL_API = RUNNING`, `PORTAL_DB = CONNECTED`, `PLATFORM_STATUS = VISIBLE`. Это критерии, а не наблюдения. После сдачи для каждой строки проверить путь и содержимое источника на указанном SHA, предел статического вывода, какое runtime-свидетельство отсутствует и когда требуется STOP. Runtime не собирать.

Следующий шаг — уже назначенная инженеру #17: сдать docs-only PR, ссылку на матрицу и полный head SHA. После сдачи архитектор проводит предметное ревью в #18. Отдельную дублирующую задачу не открывать.

Основание: [#16](https://git.aiopslab.online/aiopslab/otus-diplom/issues/16), [§4.4 спецификации](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/1b2276673a301c2b04f420a2000a22245c833265/docs/architecture/P8C_CI_RELEASE_GATE_SPEC_20261118.md#L448-L457). Не смешивать release и необязательный seed: неизвестный digest даёт `unknown`, не подтверждение различия; совпадение — STOP. Без изменений helper/pins, публикации workflow, dispatch, release, live-readiness, NetworkPolicy apply или deployment. P8C = NOT_FINAL_ACCEPTED; переход к P8D не разрешён.
