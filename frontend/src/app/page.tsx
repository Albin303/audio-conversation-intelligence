import { SectionDivider } from '@/components/ui/SectionDivider';
import { HeroSection } from '@/components/sections/HeroSection';
import { BenefitsSection } from '@/components/sections/BenefitsSection';
import { LiveStreamSection } from '@/components/sections/LiveStreamSection';
import { UploadSection } from '@/components/sections/UploadSection';
import { ConversationInputSection } from '@/components/sections/ConversationInputSection';
import { ExtractionSection } from '@/components/sections/ExtractionSection';
import { PredictionSection } from '@/components/sections/PredictionSection';
import { FollowUpAlertsSection } from '@/components/sections/FollowUpAlertsSection';


export default function Home() {
  return (
    <div className="relative flex w-full flex-col overflow-x-hidden bg-nexus-bg text-nexus-fg">
      <HeroSection />

      <SectionDivider />

      <LiveStreamSection />

      <SectionDivider />

      <UploadSection />

      <SectionDivider />

      <ConversationInputSection />

      <SectionDivider />

      <ExtractionSection />

      <SectionDivider />

      <PredictionSection />

      <SectionDivider />

      <FollowUpAlertsSection />

      <SectionDivider />

      <BenefitsSection />

    </div>
  );
}

