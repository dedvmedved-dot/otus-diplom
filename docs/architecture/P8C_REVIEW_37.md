# Review #37 — preflight #29

Решение: REQUEST CHANGES для PR #33 на `e91cb6c45665d1909bb26cee1c4fbc31f6036b37`. Runtime: NO-GO; новое окно не открыто.

1. В [документе на проверенном SHA](https://git.aiopslab.online/aiopslab/otus-diplom/src/commit/e91cb6c45665d1909bb26cee1c4fbc31f6036b37/docs/architecture/P8C_RUNTIME_29_ENGINEER_PREFLIGHT_20261119.md), включая приложение, запрещённых значений нет. PR целиком критерий не проходит: [комментарий автора](https://git.aiopslab.online/aiopslab/otus-diplom/pulls/33#issuecomment-1470) повторяет административные идентификаторы и путь, а первая ревизия PR сохраняет исходные значения. В описании PR остались прежний SHA и утверждение о сверке всех трёх параметров.
2. В документе endpoint отмечен как проверенный по паспорту `9c894af2dda4695489905df801904b9d04f02d93`; для CA и UID независимые эталоны не найдены (паспорт и inventory `82e20a2ea997c0f046a0c76600e99a6ecd97f66e`), оба блокера сохранены. Это проверка отчёта и источников, не повторное измерение endpoint.
3. Раздел о release ограничивает результат releases/tags/Actions runs Forgejo. GHCR 401 не устанавливает отсутствие пакета или запуска.
4. [Комментарий в #32](https://git.aiopslab.online/aiopslab/otus-diplom/issues/32#issuecomment-1472) содержит точный SHA и permalink.

[Доработка инженеру](https://git.aiopslab.online/aiopslab/otus-diplom/issues/38). До повторного review не сливать. Кластер и registry не опрашивались, release/dispatch и rollout не выполнялись.
