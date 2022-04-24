from __future__ import annotations

import disnake
from disnake.ui import Button, View

__all__ = ("View", "PersonalView", "PaginatorView")


class PersonalView(View):
    """View which does not respond to interactions of anyone but the invoker."""
    response = "This message is for someone else."

    def __init__(self, *, user_id: int, timeout: float | None = 180) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.user_id:
            await inter.send(self.response, ephemeral=True)
            return False

        return True


class PaginatorView(PersonalView):
    """View implementing simple button pagination."""
    buttons: list[list[Button[PaginatorView]]]

    def __init__(
        self, *, user_id: int, timeout: float | None = 180, columns_per_page: int = 3
    ) -> None:
        super().__init__(user_id=user_id, timeout=timeout)
        self.active: Button[PaginatorView] | None = None
        self.columns_per_page = int(columns_per_page)

        self.visible: list[Button[PaginatorView]] = []
        self.columns = len(max(self.buttons, key=len))
        self.page = 0

    def update_page(self) -> None:
        """Removes buttons no longer on the screen and adds those that should be on screen"""
        for button in self.visible:
            self.remove_item(button)

        self.visible.clear()
        width = self.columns_per_page
        offset = width * self.page

        for row in self.buttons:
            for button in row[offset: width+offset]:
                self.add_item(button)
                self.visible.append(button)
