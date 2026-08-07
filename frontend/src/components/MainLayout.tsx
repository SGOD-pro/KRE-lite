import React from 'react';
import { Group, Panel, Separator } from 'react-resizable-panels';
import { ChatPane } from './ChatPane';
import { SourceViewer } from './SourceViewer';

export const MainLayout: React.FC = () => {
  return (
    <div className="h-screen w-screen overflow-hidden bg-[#f8fafc]">
      <Group orientation="horizontal" className="h-full w-full">
        {/* Left Panel: Chat Pane */}
        <Panel defaultSize={50} minSize={25} className="h-full overflow-hidden">
          <ChatPane />
        </Panel>

        {/* Resizable Divider Handle */}
        <Separator className="w-2 bg-[#e2e8f0] hover:bg-[#9a4021] active:bg-[#9a4021] transition-colors cursor-col-resize relative flex items-center justify-center group focus:outline-hidden">
          <div className="w-1 h-8 rounded-full bg-[#94a3b8] group-hover:bg-white group-active:bg-white transition-colors" />
        </Separator>

        {/* Right Panel: Source Viewer */}
        <Panel defaultSize={50} minSize={25} className="h-full overflow-hidden">
          <SourceViewer />
        </Panel>
      </Group>
    </div>
  );
};
