import { MainLayout } from "@/components/main-layout"
import { CollectionsPage } from "@/components/collections-page"

export const metadata = {
  title: "Photo Admin",
  description: "Photo Collections Management",
}

export default function Home() {
  return (
    <MainLayout>
      <CollectionsPage />
    </MainLayout>
  )
}
